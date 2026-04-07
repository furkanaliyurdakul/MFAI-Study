#!/usr/bin/env python3
"""Rebuild analytics_v2 tables from Supabase DB and finalized storage payloads.

Usage examples:
  python tools/rebuild_analytics_v2.py --dry-run
  python tools/rebuild_analytics_v2.py --apply

What it does:
    1) Scans storage bucket for finalized analytics payloads only.
    2) Builds finalized session rows in public.analytics_v2_finalized_sessions.
    3) Builds per-language comparison rows in public.analytics_v2_language_results.
    4) Optionally mirrors storage interaction summaries into analytics_v2_interactions.

Notes:
    - Requires tools/ANALYTICS_V2_REBUILD.sql executed first.
    - Dry-run is default for safety.
    - This script never deletes or mutates source tables/storage objects.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
BUCKET_DEFAULT = "interview-results"
DEFAULT_EXCLUDED_LANGUAGES = {"de", "unknown"}
DEFAULT_EXCLUDED_PATH_PARTS = [
    "pilot_backup/",
    "/pilot_",
    "pilot/",
    "demo_testing/",
    "dev_testing/",
]


def to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return int(round(float(raw)))
        except Exception:
            return None
    return None


def to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return float(raw)
        except Exception:
            return None
    return None


def bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"true", "1", "yes", "y"}:
            return True
        if raw in {"false", "0", "no", "n"}:
            return False
    return None


def load_supabase_credentials() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if url and service_key:
        return url, service_key

    if SECRETS_PATH.exists():
        try:
            import tomllib  # py311+
        except Exception:
            tomllib = None

        if tomllib is not None:
            with open(SECRETS_PATH, "rb") as f:
                data = tomllib.load(f)
            sb = data.get("supabase", {})
            url = sb.get("url")
            service_key = sb.get("service_key")
            if url and service_key:
                return url, service_key

    raise RuntimeError(
        "Supabase credentials not found. Set SUPABASE_URL and SUPABASE_SERVICE_KEY "
        "or configure .streamlit/secrets.toml [supabase]."
    )


def get_client():
    try:
        from supabase import create_client
    except Exception as exc:
        raise RuntimeError("Missing dependency: supabase. Install with pip install supabase") from exc

    url, key = load_supabase_credentials()
    return create_client(url, key)


def list_bucket_files(supabase, bucket: str, prefix: str = "") -> list[str]:
    files: list[str] = []
    items = None
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            items = supabase.storage.from_(bucket).list(prefix or "")
            break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    if items is None:
        raise RuntimeError(f"Failed to list storage prefix '{prefix}' after retries: {last_exc}")

    for item in items:
        name = item.get("name", "") if isinstance(item, dict) else getattr(item, "name", "")
        item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        metadata = item.get("metadata") if isinstance(item, dict) else getattr(item, "metadata", None)

        full_path = f"{prefix}/{name}".lstrip("/") if prefix else name
        is_folder = (item_id is None and metadata is None)

        if is_folder:
            files.extend(list_bucket_files(supabase, bucket, full_path))
        else:
            files.append(full_path)

    return files


def pull_table_rows(supabase, table: str, page_size: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        result = supabase.table(table).select("*").range(offset, offset + page_size - 1).execute()
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def extract_session_id_from_path(path: str) -> str | None:
    # Expected path style: <prefix>/sessions/<session_id>/analytics/final_research_analytics.json
    m = re.search(r"/sessions/([^/]+)/", f"/{path}")
    return m.group(1) if m else None


def should_exclude_path(path: str, excluded_parts: list[str]) -> bool:
    low = path.lower()
    return any(part.lower() in low for part in excluded_parts)


def parse_final_storage_payloads(
    supabase,
    bucket: str,
    excluded_path_parts: list[str],
) -> dict[str, dict[str, Any]]:
    files = list_bucket_files(supabase, bucket)
    final_files = [
        p for p in files
        if p.endswith("/analytics/final_research_analytics.json")
    ]

    out: dict[str, dict[str, Any]] = {}
    for fpath in final_files:
        if should_exclude_path(fpath, excluded_path_parts):
            continue
        session_id = extract_session_id_from_path(fpath)
        if not session_id:
            continue
        try:
            raw = None
            last_exc: Exception | None = None
            for attempt in range(3):
                try:
                    raw = supabase.storage.from_(bucket).download(fpath)
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt < 2:
                        time.sleep(1.0 * (attempt + 1))
            if raw is None:
                raise RuntimeError(f"download failed after retries: {last_exc}")
            payload = json.loads(raw.decode("utf-8"))
            out[session_id] = {
                "path": fpath,
                "payload": payload,
            }
        except Exception as exc:
            print(f"[WARN] Could not parse storage payload {fpath}: {exc}")

    return out


def upsert_rows(supabase, table: str, rows: list[dict[str, Any]], on_conflict: str, apply: bool) -> int:
    if not rows:
        return 0
    if not apply:
        print(f"[DRY-RUN] Would upsert {len(rows)} rows into {table}")
        return len(rows)

    supabase.table(table).upsert(rows, on_conflict=on_conflict).execute()
    return len(rows)


def clear_target_tables(supabase, apply: bool) -> None:
    targets = [
        ("analytics_v2_finalized_sessions", "session_id"),
        ("analytics_v2_language_results", "language_code"),
        ("analytics_v2_interactions", "session_id"),
    ]

    for table, key_col in targets:
        if not apply:
            print(f"[DRY-RUN] Would clear existing rows from {table}")
            continue
        # Clear derived analytics tables so exclusions take full effect.
        supabase.table(table).delete().not_.is_(key_col, "null").execute()


def extract_knowledge_accuracy_pct(payload: dict[str, Any]) -> float | None:
    summary = (payload.get("summary_metrics") or {}).get("knowledge_test_summary") or {}
    v = to_float_or_none(summary.get("accuracy_percentage"))
    if v is not None:
        return v
    kt = payload.get("knowledge_test_results") or {}
    for key in ("percentage", "accuracy_percentage", "knowledge_test_score"):
        v = to_float_or_none(kt.get(key))
        if v is not None:
            return v
    return None


def build_finalized_rows(
    storage_by_session: dict[str, dict[str, Any]],
    now_iso: str,
    excluded_languages: set[str],
):
    finalized_rows: list[dict[str, Any]] = []
    interactions_rows: list[dict[str, Any]] = []

    for sid, src in storage_by_session.items():
        payload = src.get("payload") or {}
        session_info = payload.get("session_info") or {}
        language_code = (session_info.get("language_code") or "unknown").strip().lower() or "unknown"
        if language_code in excluded_languages:
            continue

        interaction_analytics = payload.get("interaction_analytics") or {}
        interaction_counts = interaction_analytics.get("interaction_counts") or {}
        learning_engagement = (payload.get("summary_metrics") or {}).get("learning_engagement") or {}
        ueq_scale_means = (payload.get("ueq_results") or {}).get("scale_means") or {}
        ueq_summary = (payload.get("summary_metrics") or {}).get("ueq_summary") or {}

        total_ai_interactions = to_int_or_none(
            learning_engagement.get("total_ai_interactions")
            or interaction_counts.get("total_user_interactions")
        )
        slide_explanations = to_int_or_none(
            learning_engagement.get("slide_explanations")
            or interaction_counts.get("slide_explanations")
        )
        manual_chat = to_int_or_none(
            learning_engagement.get("manual_chat")
            or interaction_counts.get("manual_chat")
        )

        finalized_rows.append({
            "session_id": sid,
            "language_code": language_code,
            "storage_payload_path": src.get("path"),
            "knowledge_test_accuracy_pct": extract_knowledge_accuracy_pct(payload),
            "total_session_time_seconds": to_int_or_none((payload.get("summary_metrics") or {}).get("total_session_time_seconds")),
            "total_ai_interactions": total_ai_interactions,
            "slide_explanations": slide_explanations,
            "manual_chat": manual_chat,
            "ueq_attractiveness": to_float_or_none(ueq_scale_means.get("Attractiveness")),
            "ueq_efficiency": to_float_or_none(ueq_scale_means.get("Efficiency")),
            "ueq_dependability": to_float_or_none(ueq_scale_means.get("Dependability")),
            "ueq_stimulation": to_float_or_none(ueq_scale_means.get("Stimulation")),
            "ueq_novelty": to_float_or_none(ueq_scale_means.get("Novelty")),
            "has_comment": bool_or_none(ueq_summary.get("has_comment")),
            "raw_storage": payload,
            "updated_at": now_iso,
        })

        if interaction_analytics:
            interactions_rows.append({
                "session_id": sid,
                "source": "storage_final_analytics",
                "slides_viewed": to_int_or_none(interaction_counts.get("total_user_interactions")),
                "slides_with_explanation": slide_explanations,
                "manual_chat_messages": manual_chat,
                "total_user_messages": total_ai_interactions,
                "avg_message_length": None,
                "total_duration_seconds": to_int_or_none((interaction_analytics.get("engagement_metrics") or {}).get("total_duration_seconds")),
                "extra": interaction_analytics,
                "updated_at": now_iso,
            })

    return finalized_rows, interactions_rows


def build_language_summary_rows(finalized_rows: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in finalized_rows:
        grouped.setdefault(row.get("language_code") or "unknown", []).append(row)

    def avg(values: list[float | int | None]) -> float | None:
        clean = [float(v) for v in values if v is not None]
        if not clean:
            return None
        return sum(clean) / len(clean)

    out: list[dict[str, Any]] = []
    for lang, rows in grouped.items():
        out.append({
            "language_code": lang,
            "sessions": len(rows),
            "avg_knowledge_test_accuracy_pct": avg([r.get("knowledge_test_accuracy_pct") for r in rows]),
            "avg_total_session_time_seconds": avg([r.get("total_session_time_seconds") for r in rows]),
            "avg_total_ai_interactions": avg([r.get("total_ai_interactions") for r in rows]),
            "avg_slide_explanations": avg([r.get("slide_explanations") for r in rows]),
            "avg_manual_chat": avg([r.get("manual_chat") for r in rows]),
            "avg_ueq_attractiveness": avg([r.get("ueq_attractiveness") for r in rows]),
            "avg_ueq_efficiency": avg([r.get("ueq_efficiency") for r in rows]),
            "avg_ueq_dependability": avg([r.get("ueq_dependability") for r in rows]),
            "avg_ueq_stimulation": avg([r.get("ueq_stimulation") for r in rows]),
            "avg_ueq_novelty": avg([r.get("ueq_novelty") for r in rows]),
            "comment_rate": avg([1 if r.get("has_comment") else 0 for r in rows]),
            "updated_at": now_iso,
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild analytics_v2 from DB + storage payloads")
    parser.add_argument("--apply", action="store_true", help="Write changes to Supabase (default is dry-run)")
    parser.add_argument("--bucket", default=BUCKET_DEFAULT, help="Supabase storage bucket name")
    parser.add_argument(
        "--exclude-language",
        action="append",
        default=[],
        help="Language code to exclude (repeatable). Defaults: de, unknown",
    )
    parser.add_argument(
        "--exclude-path-part",
        action="append",
        default=[],
        help="Exclude storage files whose path contains this substring (repeatable).",
    )
    args = parser.parse_args()

    apply = args.apply
    excluded_languages = {x.strip().lower() for x in (args.exclude_language or []) if x.strip()}
    if not excluded_languages:
        excluded_languages = set(DEFAULT_EXCLUDED_LANGUAGES)

    excluded_path_parts = [x.strip() for x in (args.exclude_path_part or []) if x.strip()]
    if not excluded_path_parts:
        excluded_path_parts = list(DEFAULT_EXCLUDED_PATH_PARTS)

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n=== analytics_v2 rebuild ({mode}) ===")
    print("[INFO] Non-destructive mode: only upserts into analytics_v2_* tables")
    print(f"[INFO] Excluded languages: {sorted(excluded_languages)}")
    print(f"[INFO] Excluded storage path parts: {excluded_path_parts}")

    try:
        supabase = get_client()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    now_iso = datetime.now(timezone.utc).isoformat()

    print("[1/3] Parsing finalized storage payloads...")
    storage_by_session = parse_final_storage_payloads(
        supabase,
        args.bucket,
        excluded_path_parts=excluded_path_parts,
    )
    print(f"    finalized storage payloads: {len(storage_by_session)}")

    print("[2/3] Building finalized-only rows...")
    finalized_rows, storage_interactions = build_finalized_rows(
        storage_by_session,
        now_iso,
        excluded_languages=excluded_languages,
    )
    language_rows = build_language_summary_rows(finalized_rows, now_iso)

    print(f"    analytics_v2_finalized_sessions rows: {len(finalized_rows)}")
    print(f"    analytics_v2_language_results rows: {len(language_rows)}")
    print(f"    analytics_v2_interactions(storage) rows: {len(storage_interactions)}")

    print("[3/3] Upserting...")
    clear_target_tables(supabase, apply=apply)
    finalized_written = upsert_rows(
        supabase,
        table="analytics_v2_finalized_sessions",
        rows=finalized_rows,
        on_conflict="session_id",
        apply=apply,
    )
    language_written = upsert_rows(
        supabase,
        table="analytics_v2_language_results",
        rows=language_rows,
        on_conflict="language_code",
        apply=apply,
    )
    interactions_written = upsert_rows(
        supabase,
        table="analytics_v2_interactions",
        rows=storage_interactions,
        on_conflict="session_id,source",
        apply=apply,
    )

    print("\n=== DONE ===")
    print(f"finalized_sessions upserted: {finalized_written}")
    print(f"language_results upserted: {language_written}")
    print(f"interactions upserted: {interactions_written}")

    if not apply:
        print("\nNo DB changes were made. Re-run with --apply to persist.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
