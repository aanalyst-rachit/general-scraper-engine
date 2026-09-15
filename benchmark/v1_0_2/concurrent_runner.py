from __future__ import annotations

import json
import statistics
import sys
import time
from scraper.concurrency import BoundedExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scraper.fetcher import PageFetcher
from scraper.parser import PageParser
from workload import build_workload


def run(base_url="http://127.0.0.1:8766", concurrency=4):
    workload = build_workload(base_url)
    parser = PageParser()

    def process(case):
        fetcher = PageFetcher(
            timeout=5.0,
            request_delay=0.0,
            max_requests_per_domain=100,
            max_retries=0,
        )

        started = time.perf_counter()
        page = fetcher.fetch(case.path)
        fetch_ms = (time.perf_counter() - started) * 1000

        parse_ms = 0.0
        lead = None

        if page.ok:
            started = time.perf_counter()
            lead = parser.parse(page, category="benchmark")
            parse_ms = (time.perf_counter() - started) * 1000

        return {
            "name": case.name,
            "status_code": page.status_code,
            "fetch_ok": page.ok,
            "fetch_ms": round(fetch_ms, 3),
            "parse_ms": round(parse_ms, 3),
            "total_ms": round(fetch_ms + parse_ms, 3),
            "content_bytes": len(page.html or ""),
            "lead": lead is not None,
            "parse_failure": page.ok and lead is None,
            "fetch_error": page.error,
        }

    started = time.perf_counter()
    records = []

    with BoundedExecutor(concurrency) as executor:
        records = executor.map(process, workload)

    total_ms = (time.perf_counter() - started) * 1000
    records.sort(key=lambda record: record["name"])

    fetch_latencies = [r["fetch_ms"] for r in records]
    parse_latencies = [r["parse_ms"] for r in records if r["fetch_ok"]]

    summary = {
        "benchmark": "v1.0.2",
        "mode": "bounded_concurrent_fetch_parse",
        "concurrency": concurrency,
        "base_url": base_url,
        "cases": len(records),
        "fetch_successes": sum(1 for r in records if r["fetch_ok"]),
        "fetch_failures": sum(1 for r in records if not r["fetch_ok"]),
        "parsed": sum(1 for r in records if r["fetch_ok"]),
        "parse_failures": sum(1 for r in records if r["parse_failure"]),
        "valid_leads": sum(1 for r in records if r["lead"]),
        "total_ms": round(total_ms, 3),
        "mean_fetch_ms": round(statistics.mean(fetch_latencies), 3),
        "median_fetch_ms": round(statistics.median(fetch_latencies), 3),
        "mean_parse_ms": round(statistics.mean(parse_latencies), 3),
        "median_parse_ms": round(statistics.median(parse_latencies), 3),
        "total_content_bytes": sum(r["content_bytes"] for r in records),
        "records": records,
    }

    output = ROOT / "benchmark" / "v1_0_2" / "results" / f"concurrent_c{concurrency}.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("===== V1.0.2 CONCURRENT BASELINE =====")
    print("Cases:", summary["cases"])
    print("Concurrency:", summary["concurrency"])
    print("Fetch successes:", summary["fetch_successes"])
    print("Fetch failures:", summary["fetch_failures"])
    print("Valid leads:", summary["valid_leads"])
    print("Total ms:", summary["total_ms"])
    print("Mean fetch ms:", summary["mean_fetch_ms"])
    print("Median fetch ms:", summary["median_fetch_ms"])
    print("Mean parse ms:", summary["mean_parse_ms"])
    print("Median parse ms:", summary["median_parse_ms"])
    print("Content bytes:", summary["total_content_bytes"])
    print("Results:", output)


if __name__ == "__main__":
    run()
