#!/usr/bin/env python3
"""Export a conference-ready analysis pack from Supabase analytics_v2 views.

What this script does:
1) Pulls analysis-ready datasets from Supabase views/tables.
2) Exports CSV files into a timestamped folder.
3) Creates a few ready-to-use PNG charts when matplotlib is available.
4) Writes a short markdown summary with sample sizes and key averages.

Usage:
  python tools/export_analysis_pack.py
  python tools/export_analysis_pack.py --out-dir output/analysis_pack/custom_run
"""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "output" / "analysis_pack"


def load_supabase_credentials() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if url and service_key:
        return url, service_key

    if SECRETS_PATH.exists():
        try:
            import tomllib
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


def fetch_all_rows(supabase, relation: str, page_size: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        result = supabase.table(relation).select("*").range(offset, offset + page_size - 1).execute()
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def csv_safe_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list)):
        return str(value)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return

    all_keys: list[str] = []
    key_set: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in key_set:
                key_set.add(k)
                all_keys.append(k)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_safe_value(row.get(k)) for k in all_keys})


def try_make_plots(out_dir: Path, datasets: dict[str, list[dict[str, Any]]]) -> list[str]:
    messages: list[str] = []
    try:
        import matplotlib.pyplot as plt
    except Exception:
        messages.append("matplotlib not installed; skipped PNG chart generation")
        return messages

    compare = datasets.get("analytics_v2_compare_languages", [])
    descriptives = datasets.get("analytics_v2_descriptives_long", [])

    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    if compare:
        languages = [str(r.get("language_code")) for r in compare]
        sessions = [float(r.get("sessions") or 0.0) for r in compare]
        avg_score = [float(r.get("avg_knowledge_test_accuracy_pct") or 0.0) for r in compare]
        avg_ai = [float(r.get("avg_total_ai_interactions") or 0.0) for r in compare]

        plt.figure(figsize=(9, 5))
        plt.bar(languages, sessions)
        plt.title("Sessions per Language")
        plt.xlabel("Language")
        plt.ylabel("Sessions")
        plt.tight_layout()
        plt.savefig(plots_dir / "sessions_per_language.png", dpi=150)
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.bar(languages, avg_score)
        plt.title("Average Knowledge Test Accuracy by Language")
        plt.xlabel("Language")
        plt.ylabel("Avg Accuracy (%)")
        plt.tight_layout()
        plt.savefig(plots_dir / "avg_knowledge_accuracy_by_language.png", dpi=150)
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.bar(languages, avg_ai)
        plt.title("Average AI Interactions by Language")
        plt.xlabel("Language")
        plt.ylabel("Avg Interactions")
        plt.tight_layout()
        plt.savefig(plots_dir / "avg_ai_interactions_by_language.png", dpi=150)
        plt.close()

    if descriptives:
        metric = "knowledge_test_accuracy_pct"
        metric_rows = [r for r in descriptives if str(r.get("metric")) == metric]
        if metric_rows:
            languages = [str(r.get("language_code")) for r in metric_rows]
            medians = [float(r.get("median") or 0.0) for r in metric_rows]
            q1 = [float(r.get("q1") or 0.0) for r in metric_rows]
            q3 = [float(r.get("q3") or 0.0) for r in metric_rows]
            yerr_low = [m - a for m, a in zip(medians, q1)]
            yerr_high = [b - m for m, b in zip(medians, q3)]

            plt.figure(figsize=(9, 5))
            plt.errorbar(languages, medians, yerr=[yerr_low, yerr_high], fmt="o", capsize=4)
            plt.title("Knowledge Accuracy Median and IQR by Language")
            plt.xlabel("Language")
            plt.ylabel("Accuracy (%)")
            plt.tight_layout()
            plt.savefig(plots_dir / "knowledge_accuracy_median_iqr.png", dpi=150)
            plt.close()

    messages.append("PNG charts generated in plots/")
    return messages


def write_summary(out_dir: Path, datasets: dict[str, list[dict[str, Any]]]) -> None:
    compare = datasets.get("analytics_v2_compare_languages", [])
    quality = datasets.get("analytics_v2_data_quality_by_language", [])

    lines: list[str] = []
    lines.append("# Analysis Pack Summary")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    total_sessions = 0
    for row in compare:
        total_sessions += int(float(row.get("sessions") or 0))

    lines.append(f"Total sessions in comparison set: {total_sessions}")
    lines.append(f"Languages included: {', '.join(str(r.get('language_code')) for r in compare)}")
    lines.append("")
    lines.append("## Group Overview")
    for row in compare:
        lang = row.get("language_code")
        sessions = row.get("sessions")
        score = row.get("avg_knowledge_test_accuracy_pct")
        ai = row.get("avg_total_ai_interactions")
        lines.append(f"- {lang}: n={sessions}, avg_score={score}, avg_ai_interactions={ai}")

    lines.append("")
    lines.append("## Data Quality")
    for row in quality:
        lang = row.get("language_code")
        know = row.get("knowledge_non_missing_rate")
        ueq = row.get("ueq_attr_non_missing_rate")
        lines.append(f"- {lang}: knowledge_non_missing={know}, ueq_non_missing={ueq}")

    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export analysis pack from Supabase analytics_v2 views")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults to output/analysis_pack/<timestamp>")
    args = parser.parse_args()

    if args.out_dir.strip():
        out_dir = Path(args.out_dir).resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = DEFAULT_OUTPUT_ROOT / stamp

    print(f"[INFO] Output directory: {out_dir}")

    try:
        supabase = get_client()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    relations = [
        "analytics_v2_export_dataset",
        "analytics_v2_descriptives_long",
        "analytics_v2_data_quality_by_language",
        "analytics_v2_within_group_correlations",
        "analytics_v2_compare_languages",
        "analytics_v2_variable_catalog",
    ]

    datasets: dict[str, list[dict[str, Any]]] = {}

    for rel in relations:
        print(f"[FETCH] {rel}")
        rows = fetch_all_rows(supabase, rel)
        datasets[rel] = rows
        write_csv(out_dir / f"{rel}.csv", rows)
        print(f"        rows: {len(rows)}")

    write_summary(out_dir, datasets)
    plot_msgs = try_make_plots(out_dir, datasets)

    print("\n=== DONE ===")
    for rel in relations:
        print(f"- {rel}.csv")
    print("- README.md")
    for msg in plot_msgs:
        print(f"- {msg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
