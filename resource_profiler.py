"""Runtime resource profiler for Streamlit cloud debugging.

Outputs periodic process diagnostics to stdout so logs are visible in cloud
platform terminals. Includes optional stress mode to force failure conditions.
"""

from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Any

try:
    import psutil
except Exception:
    psutil = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


def _safe_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _safe_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(max(value, 0))
    i = 0
    while x >= 1024 and i < len(units) - 1:
        x /= 1024.0
        i += 1
    return f"{x:.2f} {units[i]}"


def _shallow_size(obj: Any) -> int:
    try:
        return sys.getsizeof(obj)
    except Exception:
        return 0


def _deep_size(obj: Any, max_depth: int = 4, max_items: int = 20000) -> int:
    """Approximate deep size of object graph with hard limits."""
    seen_ids: set[int] = set()
    stack: list[tuple[Any, int]] = [(obj, 0)]
    total = 0
    visited = 0

    while stack and visited < max_items:
        current, depth = stack.pop()
        oid = id(current)
        if oid in seen_ids:
            continue
        seen_ids.add(oid)
        visited += 1
        total += _shallow_size(current)

        if depth >= max_depth:
            continue

        try:
            if isinstance(current, dict):
                stack.extend((k, depth + 1) for k in current.keys())
                stack.extend((v, depth + 1) for v in current.values())
            elif isinstance(current, (list, tuple, set, frozenset)):
                stack.extend((item, depth + 1) for item in current)
            elif hasattr(current, "__dict__"):
                stack.append((vars(current), depth + 1))
        except Exception:
            continue

    return total


class ResourceProfiler:
    def __init__(self) -> None:
        self.enabled = _env_bool("RESOURCE_PROFILING", False)
        if psutil is None:
            self.enabled = False
        self.interval_sec = max(1, _safe_int("RESOURCE_PROFILING_INTERVAL_SEC", 20))
        self.top_n = max(1, _safe_int("RESOURCE_PROFILING_TOP_N", 12))
        self.object_sample_limit = max(1000, _safe_int("RESOURCE_OBJECT_SAMPLE_LIMIT", 40000))

        self.stress_mode = os.getenv("RESOURCE_STRESS_MODE", "off").strip().lower()
        if self.stress_mode not in {"off", "memory", "cpu", "both"}:
            self.stress_mode = "off"
        self.stress_mb_per_sec = max(1, _safe_int("RESOURCE_STRESS_MB_PER_SEC", 16))
        self.stress_max_mb = max(0, _safe_int("RESOURCE_STRESS_MAX_MB", 0))
        self.stress_cpu_workers = max(1, _safe_int("RESOURCE_STRESS_CPU_WORKERS", 1))
        self.stress_print_interval = max(1.0, _safe_float("RESOURCE_STRESS_PRINT_INTERVAL_SEC", 5.0))

        self._proc = psutil.Process(os.getpid()) if psutil is not None else None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stress_threads: list[threading.Thread] = []
        self._mem_chunks: list[bytearray] = []
        self._lock = threading.Lock()

        self._last_emit = 0.0
        self._last_stress_emit = 0.0
        self._snapshot_sink = None

    def start(self) -> None:
        if psutil is None:
            print("[RESOURCE] profiler_disabled reason=psutil_unavailable")
            return
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return

        if not tracemalloc.is_tracing():
            tracemalloc.start(25)

        self._proc.cpu_percent(interval=None)
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="resource-profiler",
            daemon=True,
        )
        self._thread.start()

        if self.stress_mode in {"memory", "both"}:
            t = threading.Thread(target=self._run_memory_stress, name="resource-stress-memory", daemon=True)
            t.start()
            self._stress_threads.append(t)

        if self.stress_mode in {"cpu", "both"}:
            for i in range(self.stress_cpu_workers):
                t = threading.Thread(target=self._run_cpu_stress, name=f"resource-stress-cpu-{i}", daemon=True)
                t.start()
                self._stress_threads.append(t)

        self._emit_header()

    def stop(self) -> None:
        self._stop_event.set()

    def set_snapshot_sink(self, sink_callable) -> None:
        """Register callback that receives structured snapshot payloads."""
        self._snapshot_sink = sink_callable

    def emit_once(self, tag: str = "manual") -> None:
        if not self.enabled:
            return
        try:
            self._emit_snapshot(tag=tag)
        except Exception as exc:
            print(f"[RESOURCE] emit_once_failed error={type(exc).__name__}: {exc}")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            if now - self._last_emit >= self.interval_sec:
                self._last_emit = now
                try:
                    self._emit_snapshot(tag="periodic")
                except Exception as exc:
                    print(f"[RESOURCE] periodic_emit_failed error={type(exc).__name__}: {exc}")
            time.sleep(1.0)

    def _emit_header(self) -> None:
        print("[RESOURCE] profiler_started")
        print(
            "[RESOURCE] config "
            f"interval_sec={self.interval_sec} top_n={self.top_n} "
            f"stress_mode={self.stress_mode} stress_mb_per_sec={self.stress_mb_per_sec} "
            f"stress_max_mb={self.stress_max_mb} stress_cpu_workers={self.stress_cpu_workers}"
        )

    def _emit_snapshot(self, tag: str) -> None:
        if self._proc is None:
            return
        ts = datetime.now(timezone.utc).isoformat()

        with self._proc.oneshot():
            mem = self._proc.memory_info()
            try:
                full_mem = self._proc.memory_full_info()
                uss = getattr(full_mem, "uss", 0)
                pss = getattr(full_mem, "pss", 0)
            except Exception:
                uss = 0
                pss = 0

            cpu_percent = self._proc.cpu_percent(interval=None)
            cpu_times = self._proc.cpu_times()
            thr_count = self._proc.num_threads()
            rss = mem.rss
            vms = mem.vms
            open_files = self._proc.open_files()
            children = self._proc.children(recursive=True)

            try:
                io = self._proc.io_counters()
            except Exception:
                io = None

        print("[RESOURCE]" + "=" * 70)
        print(f"[RESOURCE] snapshot tag={tag} ts={ts} pid={self._proc.pid}")
        print(
            "[RESOURCE] process "
            f"cpu_percent={cpu_percent:.2f} rss={_format_bytes(rss)} vms={_format_bytes(vms)} "
            f"uss={_format_bytes(uss)} pss={_format_bytes(pss)} threads={thr_count}"
        )
        print(
            "[RESOURCE] cpu_times "
            f"user={cpu_times.user:.2f}s system={cpu_times.system:.2f}s"
        )

        if io:
            print(
                "[RESOURCE] io "
                f"read_count={io.read_count} write_count={io.write_count} "
                f"read_bytes={_format_bytes(io.read_bytes)} write_bytes={_format_bytes(io.write_bytes)}"
            )

        print(f"[RESOURCE] open_files count={len(open_files)}")
        for f in open_files[: self.top_n]:
            print(f"[RESOURCE] open_file path={f.path}")

        child_mem = 0
        child_cpu = 0.0
        for c in children:
            try:
                child_mem += c.memory_info().rss
                child_cpu += c.cpu_percent(interval=None)
            except Exception:
                continue
        print(
            "[RESOURCE] children "
            f"count={len(children)} total_rss={_format_bytes(child_mem)} total_cpu_percent={child_cpu:.2f}"
        )

        self._emit_thread_cpu()
        self._emit_gc_type_breakdown()
        self._emit_tracemalloc_breakdown()

        if self.stress_mode in {"memory", "both"}:
            total_stress_mb = sum(len(x) for x in self._mem_chunks) / (1024 * 1024)
            print(f"[RESOURCE] stress_memory allocated_mb={total_stress_mb:.2f}")

        snapshot_payload = {
            "event_type": "snapshot",
            "tag": tag,
            "timestamp": ts,
            "pid": self._proc.pid,
            "cpu_percent": cpu_percent,
            "rss_bytes": rss,
            "vms_bytes": vms,
            "uss_bytes": uss,
            "pss_bytes": pss,
            "thread_count": thr_count,
            "open_files_count": len(open_files),
            "open_files": [f.path for f in open_files[: self.top_n]],
            "children_count": len(children),
            "children_total_rss_bytes": child_mem,
            "children_total_cpu_percent": child_cpu,
            "cpu_user_seconds": cpu_times.user,
            "cpu_system_seconds": cpu_times.system,
            "io": {
                "read_count": getattr(io, "read_count", 0) if io else 0,
                "write_count": getattr(io, "write_count", 0) if io else 0,
                "read_bytes": getattr(io, "read_bytes", 0) if io else 0,
                "write_bytes": getattr(io, "write_bytes", 0) if io else 0,
            },
            "stress_mode": self.stress_mode,
            "stress_allocated_mb": (sum(len(x) for x in self._mem_chunks) / (1024 * 1024)) if self.stress_mode in {"memory", "both"} else 0,
        }
        self._push_snapshot(snapshot_payload)

    def _emit_thread_cpu(self) -> None:
        try:
            native_to_name = {}
            for t in threading.enumerate():
                nid = getattr(t, "native_id", None)
                if nid is not None:
                    native_to_name[nid] = t.name

            thread_rows = []
            for t in self._proc.threads():
                thread_rows.append(
                    (
                        t.id,
                        native_to_name.get(t.id, "unknown"),
                        t.user_time,
                        t.system_time,
                    )
                )
            thread_rows.sort(key=lambda x: (x[2] + x[3]), reverse=True)

            print(f"[RESOURCE] threads_top count={len(thread_rows)}")
            for tid, name, ut, st in thread_rows[: self.top_n]:
                print(f"[RESOURCE] thread tid={tid} name={name} user={ut:.2f}s system={st:.2f}s")
        except Exception as exc:
            print(f"[RESOURCE] thread_cpu_failed error={type(exc).__name__}: {exc}")

    def _emit_gc_type_breakdown(self) -> None:
        try:
            objs = gc.get_objects()
            counts = Counter(type(o).__name__ for o in objs)
            top_counts = counts.most_common(self.top_n)
            print(f"[RESOURCE] gc_objects total={len(objs)}")
            for tname, cnt in top_counts:
                print(f"[RESOURCE] gc_type type={tname} count={cnt}")

            size_by_type = Counter()
            sampled = 0
            for o in objs:
                sampled += 1
                if sampled > self.object_sample_limit:
                    break
                tname = type(o).__name__
                size_by_type[tname] += _shallow_size(o)
            for tname, bytes_used in size_by_type.most_common(self.top_n):
                print(f"[RESOURCE] gc_type_size type={tname} sampled_bytes={_format_bytes(bytes_used)}")
        except Exception as exc:
            print(f"[RESOURCE] gc_breakdown_failed error={type(exc).__name__}: {exc}")

    def _emit_tracemalloc_breakdown(self) -> None:
        if not tracemalloc.is_tracing():
            return
        try:
            snap = tracemalloc.take_snapshot()
            top = snap.statistics("filename")
            print(f"[RESOURCE] tracemalloc_top files={len(top)}")
            for stat in top[: self.top_n]:
                print(
                    "[RESOURCE] tm_file "
                    f"file={stat.traceback[0].filename} size={_format_bytes(stat.size)} count={stat.count}"
                )
        except Exception as exc:
            print(f"[RESOURCE] tracemalloc_failed error={type(exc).__name__}: {exc}")

    def emit_session_state_breakdown(self, session_state: Any) -> None:
        if not self.enabled:
            return
        try:
            rows = []
            for key in list(session_state.keys()):
                try:
                    val = session_state.get(key)
                    size = _deep_size(val)
                    rows.append((key, size, type(val).__name__))
                except Exception:
                    rows.append((key, 0, "unknown"))
            rows.sort(key=lambda x: x[1], reverse=True)
            print(f"[RESOURCE] session_state_keys count={len(rows)}")
            for key, size, tname in rows[: self.top_n]:
                print(f"[RESOURCE] session_state key={key} type={tname} approx_size={_format_bytes(size)}")

            self._push_snapshot(
                {
                    "event_type": "session_state",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "keys_count": len(rows),
                    "top_keys": [
                        {"key": key, "type": tname, "approx_size_bytes": size}
                        for key, size, tname in rows[: self.top_n]
                    ],
                }
            )
        except Exception as exc:
            print(f"[RESOURCE] session_state_breakdown_failed error={type(exc).__name__}: {exc}")

    def _push_snapshot(self, payload: dict[str, Any]) -> None:
        if self._snapshot_sink is None:
            return
        try:
            self._snapshot_sink(payload)
        except Exception as exc:
            print(f"[RESOURCE] sink_failed error={type(exc).__name__}: {exc}")

    def _run_memory_stress(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                total_mb = sum(len(x) for x in self._mem_chunks) / (1024 * 1024)
                if self.stress_max_mb <= 0 or total_mb < self.stress_max_mb:
                    self._mem_chunks.append(bytearray(self.stress_mb_per_sec * 1024 * 1024))

            now = time.time()
            if now - self._last_stress_emit >= self.stress_print_interval:
                self._last_stress_emit = now
                total_mb = sum(len(x) for x in self._mem_chunks) / (1024 * 1024)
                print(f"[RESOURCE] stress_tick mode=memory allocated_mb={total_mb:.2f}")
            time.sleep(1.0)

    def _run_cpu_stress(self) -> None:
        while not self._stop_event.is_set():
            start = time.perf_counter()
            x = 0
            while (time.perf_counter() - start) < 0.9 and not self._stop_event.is_set():
                x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
            _ = x
            time.sleep(0.1)


_profiler_singleton: ResourceProfiler | None = None


def get_resource_profiler() -> ResourceProfiler:
    global _profiler_singleton
    if _profiler_singleton is None:
        _profiler_singleton = ResourceProfiler()
    return _profiler_singleton
