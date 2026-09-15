from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scraper.fetcher import PageFetcher
from workload import build_workload


def classify_failure(result):
    if result.ok:
        return None
    if result.error:
        error = result.error.lower()
        if "robot" in error:
            return "robots"
        if "timeout" in error:
            return "timeout"
        if "http" in error or "status" in error:
            return "http"
        return "error"
    if result.status_code >= 400:
        return "http"
    if not result.html:
        return "empty"
    return "unknown"


def run(base_url="http://127.0.0.1:8766"):
    workload = build_workload(base_url)
    fetcher = PageFetcher(
        timeout=5.0,
        request_delay=0.0,
        max_requests_per_domain=100,
        max_retries=0,
    )

    started = time.perf_counter()
    records = []

    for case in workload:
        page_started = time.perf_counter()
        result = fetcher.fetch(case.path)
        elapsed_ms = (time.perf_counter() - page_started) * 1000

        records.append({
            "name": case.name,
            "url": case.path,
            "expected_status": case.expected_status,
            "expected_success": case.expected_success,
            "status_code": result.status_code,
            "ok": result.ok,
            "elapsed_ms": round(elapsed_ms, 3),
            "content_bytes": len(result.html or ""),
            "error": result.error,
            "failure_category": classify_failure(result),
        })

    total_ms = (time.perf_counter() - started) * 1000
    latencies = [record["elapsed_ms"] for record in records]
    failures = [record for record in records if not record["ok"]]

    failure_categories = {}
    for record in failures:
        category = record["failure_category"] or "unknown"
        failure_categories[category] = failure_categories.get(category, 0) + 1

    summary = {
        "benchmark": "v1.0.2",
        "mode": "sequential_fetch_baseline",
        "base_url": base_url,
        "cases": len(records),
        "successful_fetches": len(records) - len(failures),
        "failed_fetches": len(failures),
        "total_content_bytes": sum(record["content_bytes"] for record in records),
        "failure_categories": failure_categories,
        "expectation_mismatches": [
            record["name"]
            for record in records
            if record["status_code"] != record["expected_status"]
            or record["ok"] != record["expected_success"]
        ],
        "total_ms": round(total_ms, 3),
        "mean_fetch_ms": round(statistics.mean(latencies), 3),
        "median_fetch_ms": round(statistics.median(latencies), 3),
        "min_fetch_ms": round(min(latencies), 3),
        "max_fetch_ms": round(max(latencies), 3),
        "records": records,
    }

    output = ROOT / "benchmark" / "v1_0_2" / "results" / "baseline_fetch.json"
    output.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("===== V1.0.2 FETCH BASELINE =====")
    print("Cases:", summary["cases"])
    print("Successful fetches:", summary["successful_fetches"])
    print("Failed fetches:", summary["failed_fetches"])
    print("Total ms:", summary["total_ms"])
    print("Mean fetch ms:", summary["mean_fetch_ms"])
    print("Median fetch ms:", summary["median_fetch_ms"])
    print("Min fetch ms:", summary["min_fetch_ms"])
    print("Max fetch ms:", summary["max_fetch_ms"])
    print("Content bytes:", summary["total_content_bytes"])
    print("Failure categories:", summary["failure_categories"])
    print("Expectation mismatches:", summary["expectation_mismatches"])
    print("Results:", output)

    print()
    print("===== PER CASE =====")
    for record in records:
        print(
            "{:<20} status={:<3} time={:>9.3f} ms ok={} bytes={} failure={}".format(
                record["name"],
                record["status_code"],
                record["elapsed_ms"],
                record["ok"],
                record["content_bytes"],
                record["failure_category"],
            )
        )

    return summary


if __name__ == "__main__":
    run()
