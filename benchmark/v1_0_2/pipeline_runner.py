from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scraper.fetcher import PageFetcher
from scraper.parser import PageParser
from workload import build_workload


def run(base_url="http://127.0.0.1:8766"):
    workload = build_workload(base_url)
    fetcher = PageFetcher(
        timeout=5.0,
        request_delay=0.0,
        max_requests_per_domain=100,
        max_retries=0,
    )
    parser = PageParser()

    run_started = time.perf_counter()
    records = []

    for case in workload:
        case_started = time.perf_counter()

        fetch_started = time.perf_counter()
        page = fetcher.fetch(case.path)
        fetch_ms = (time.perf_counter() - fetch_started) * 1000

        parse_ms = 0.0
        lead = None

        if page.ok:
            parse_started = time.perf_counter()
            lead = parser.parse(page, category="benchmark")
            parse_ms = (time.perf_counter() - parse_started) * 1000

        total_case_ms = (time.perf_counter() - case_started) * 1000

        records.append({
            "name": case.name,
            "status_code": page.status_code,
            "fetch_ok": page.ok,
            "fetch_ms": round(fetch_ms, 3),
            "parse_ms": round(parse_ms, 3),
            "total_ms": round(total_case_ms, 3),
            "content_bytes": len(page.html or ""),
            "lead": lead is not None,
            "parse_failure": page.ok and lead is None,
            "fetch_error": page.error,
        })

    total_ms = (time.perf_counter() - run_started) * 1000
    fetch_latencies = [r["fetch_ms"] for r in records]
    parse_latencies = [r["parse_ms"] for r in records if r["fetch_ok"]]
    case_latencies = [r["total_ms"] for r in records]
    fetch_failures = [r for r in records if not r["fetch_ok"]]
    parse_failures = [r for r in records if r["parse_failure"]]

    summary = {
        "benchmark": "v1.0.2",
        "mode": "sequential_fetch_parse_baseline",
        "base_url": base_url,
        "cases": len(records),
        "fetched": len(records),
        "fetch_successes": len(records) - len(fetch_failures),
        "fetch_failures": len(fetch_failures),
        "parsed": len(records) - len(fetch_failures),
        "parse_failures": len(parse_failures),
        "valid_leads": sum(1 for r in records if r["lead"]),
        "total_ms": round(total_ms, 3),
        "mean_fetch_ms": round(statistics.mean(fetch_latencies), 3),
        "median_fetch_ms": round(statistics.median(fetch_latencies), 3),
        "mean_parse_ms": round(statistics.mean(parse_latencies), 3),
        "median_parse_ms": round(statistics.median(parse_latencies), 3),
        "mean_case_ms": round(statistics.mean(case_latencies), 3),
        "total_content_bytes": sum(r["content_bytes"] for r in records),
        "records": records,
    }

    output = ROOT / "benchmark" / "v1_0_2" / "results" / "baseline_pipeline.json"
    output.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("===== V1.0.2 PIPELINE BASELINE =====")
    print("Cases:", summary["cases"])
    print("Fetch successes:", summary["fetch_successes"])
    print("Fetch failures:", summary["fetch_failures"])
    print("Parsed:", summary["parsed"])
    print("Parse failures:", summary["parse_failures"])
    print("Valid leads:", summary["valid_leads"])
    print("Total ms:", summary["total_ms"])
    print("Mean fetch ms:", summary["mean_fetch_ms"])
    print("Median fetch ms:", summary["median_fetch_ms"])
    print("Mean parse ms:", summary["mean_parse_ms"])
    print("Median parse ms:", summary["median_parse_ms"])
    print("Mean case ms:", summary["mean_case_ms"])
    print("Content bytes:", summary["total_content_bytes"])
    print("Results:", output)

    print()
    print("===== PER CASE =====")
    for record in records:
        print(
            "{:<20} fetch={:>8.3f} ms parse={:>8.3f} ms "
            "total={:>8.3f} ms status={} lead={} error={}".format(
                record["name"],
                record["fetch_ms"],
                record["parse_ms"],
                record["total_ms"],
                record["status_code"],
                record["lead"],
                record["fetch_error"],
            )
        )

    return summary


if __name__ == "__main__":
    run()
