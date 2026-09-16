from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scraper.acquisition import CachedFetcher, FetchRequest, HTTPFetcherAdapter
from scraper.cache.fetch import FetchCache
from scraper.fetcher import PageFetcher


def benchmark_baseline(
    url: str,
    iterations: int,
) -> tuple[dict, int]:
    fetcher = PageFetcher(
        timeout=5.0,
        request_delay=0.0,
        max_requests_per_domain=100,
        max_retries=0,
    )

    samples = []
    results = []

    for _ in range(iterations):
        started = time.perf_counter()
        result = fetcher.fetch(url)
        samples.append((time.perf_counter() - started) * 1000)
        results.append(result)

    return (
        {
            "iterations": iterations,
            "mean_ms": statistics.mean(samples),
            "median_ms": statistics.median(samples),
            "min_ms": min(samples),
            "max_ms": max(samples),
            "successful_fetches": sum(result.ok for result in results),
            "content_bytes": len(results[0].html or ""),
        },
        iterations,
    )


def benchmark_cached(
    url: str,
    iterations: int,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="fetch-cache-benchmark-") as tmp:
        database_path = Path(tmp) / "fetch.duckdb"
        underlying = PageFetcher(
            timeout=5.0,
            request_delay=0.0,
            max_requests_per_domain=100,
            max_retries=0,
        )

        fetch_calls = 0

        class CountingFetcher:
            def fetch(self, request):
                nonlocal fetch_calls
                fetch_calls += 1
                return underlying.fetch(request)

        acquisition = HTTPFetcherAdapter(CountingFetcher())
        cache = FetchCache(database_path)
        fetcher = CachedFetcher(
            acquisition,
            cache,
            acquisition_strategy="http",
        )

        samples = []
        results = []

        for _ in range(iterations):
            started = time.perf_counter()
            result = fetcher.fetch(FetchRequest(url))
            samples.append((time.perf_counter() - started) * 1000)
            results.append(result)

        cache_entry = cache.get(
            url=url,
            acquisition_strategy="http",
        )

        database_size_bytes = database_path.stat().st_size
        cache.close()

        return {
            "iterations": iterations,
            "cache_misses": 1,
            "cache_hits": iterations - 1,
            "hit_rate": (iterations - 1) / iterations,
            "mean_ms": statistics.mean(samples),
            "median_ms": statistics.median(samples),
            "min_ms": min(samples),
            "max_ms": max(samples),
            "successful_fetches": sum(result.ok for result in results),
            "content_bytes": len(results[0].html or ""),
            "underlying_fetch_calls": fetch_calls,
            "cached_content_hash": cache_entry.content_hash
            if cache_entry is not None
            else None,
            "database_size_bytes": database_size_bytes,
        }


def run(base_url: str = "http://127.0.0.1:8766") -> dict:
    iterations = 20
    url = f"{base_url}/static"

    baseline, baseline_calls = benchmark_baseline(
        url,
        iterations,
    )
    cached = benchmark_cached(
        url,
        iterations,
    )

    result = {
        "benchmark": "fetch-cache-benefit",
        "workload": {
            "url": url,
            "iterations": iterations,
            "acquisition_strategy": "http",
        },
        "baseline": {
            **baseline,
            "underlying_fetch_calls": baseline_calls,
        },
        "cached": cached,
        "speedup": baseline["mean_ms"] / cached["mean_ms"],
        "mean_latency_reduction": (
            1 - cached["mean_ms"] / baseline["mean_ms"]
        ),
        "underlying_call_reduction": (
            1 - cached["underlying_fetch_calls"] / baseline_calls
        ),
    }

    output = ROOT / "benchmark" / "fetch_cache" / "results" / "baseline.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print("===== FETCH CACHE BENEFIT =====")
    print("URL:", url)
    print("Iterations:", iterations)
    print("Baseline mean ms:", round(baseline["mean_ms"], 3))
    print("Cached mean ms:", round(cached["mean_ms"], 3))
    print("Baseline median ms:", round(baseline["median_ms"], 3))
    print("Cached median ms:", round(cached["median_ms"], 3))
    print("Speedup:", round(result["speedup"], 3), "x")
    print(
        "Mean latency reduction:",
        round(result["mean_latency_reduction"] * 100, 2),
        "%",
    )
    print(
        "Underlying call reduction:",
        round(result["underlying_call_reduction"] * 100, 2),
        "%",
    )
    print("Cache hit rate:", round(cached["hit_rate"] * 100, 2), "%")
    print("Content bytes:", cached["content_bytes"])
    print("Database size:", cached["database_size_bytes"], "bytes")
    print("Results:", output)

    return result


if __name__ == "__main__":
    run()
