from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scraper.concurrency import BoundedExecutor


RESULTS = ROOT / "benchmark" / "batch_processing" / "results"
ITEM_COUNT = 40
WORK_DELAY = 0.05
FAILURE_INDICES = {7, 19, 31}


def work(value: int) -> int:
    time.sleep(WORK_DELAY)
    if value in FAILURE_INDICES:
        raise RuntimeError(f"synthetic failure: {value}")
    return value * 2


def run_sequential(values: list[int]) -> dict[str, object]:
    started = time.perf_counter()
    results = []
    failures = 0

    for value in values:
        try:
            results.append(work(value))
        except Exception:
            failures += 1

    total_ms = (time.perf_counter() - started) * 1000
    return {
        "mode": "sequential",
        "concurrency": 1,
        "items": len(values),
        "successful_items": len(results),
        "failed_items": failures,
        "total_ms": round(total_ms, 3),
        "throughput_items_per_sec": round(len(values) / (total_ms / 1000), 3),
    }


def run_batch(values: list[int], concurrency: int) -> dict[str, object]:
    started = time.perf_counter()

    with BoundedExecutor(concurrency) as executor:
        results = executor.map_isolated(work, values)

    total_ms = (time.perf_counter() - started) * 1000
    successful = sum(1 for item in results if item.ok)
    failed = sum(1 for item in results if not item.ok)

    return {
        "mode": "bounded_batch_map_isolated",
        "concurrency": concurrency,
        "items": len(values),
        "successful_items": successful,
        "failed_items": failed,
        "total_ms": round(total_ms, 3),
        "throughput_items_per_sec": round(len(values) / (total_ms / 1000), 3),
    }


def main() -> None:
    values = list(range(ITEM_COUNT))

    baseline = run_sequential(values)
    batch_c4 = run_batch(values, 4)
    batch_c8 = run_batch(values, 8)

    baseline_ms = baseline["total_ms"]
    batch_c4["speedup_vs_sequential"] = round(baseline_ms / batch_c4["total_ms"], 3)
    batch_c8["speedup_vs_sequential"] = round(baseline_ms / batch_c8["total_ms"], 3)

    summary = {
        "benchmark": "phase-15-batch-processing",
        "workload_items": ITEM_COUNT,
        "work_delay_ms": WORK_DELAY * 1000,
        "intentional_failures": len(FAILURE_INDICES),
        "baseline": baseline,
        "batch_c4": batch_c4,
        "batch_c8": batch_c8,
    }

    output = RESULTS / "results.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("===== PHASE 15 BATCH PROCESSING BENCHMARK =====")
    print("Items:", ITEM_COUNT)
    print("Work delay ms:", WORK_DELAY * 1000)
    print("Intentional failures:", len(FAILURE_INDICES))
    print("Sequential total ms:", baseline["total_ms"])
    print("C4 total ms:", batch_c4["total_ms"])
    print("C4 throughput:", batch_c4["throughput_items_per_sec"])
    print("C4 speedup:", batch_c4["speedup_vs_sequential"])
    print("C8 total ms:", batch_c8["total_ms"])
    print("C8 throughput:", batch_c8["throughput_items_per_sec"])
    print("C8 speedup:", batch_c8["speedup_vs_sequential"])
    print("C4 failures:", batch_c4["failed_items"])
    print("C8 failures:", batch_c8["failed_items"])
    print("Results:", output)


if __name__ == "__main__":
    main()
