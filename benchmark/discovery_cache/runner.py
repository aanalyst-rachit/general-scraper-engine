from __future__ import annotations

import json
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from scraper.cache.discovery import DiscoveryCache
from scraper.discovery import DiscoveredPage, SearchRequest, WebDiscovery


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmark" / "discovery_cache" / "results"


@dataclass
class CountingProvider:
    delay_seconds: float = 0.01
    calls: int = 0

    def search(self, query: str, limit: int = 20) -> list[DiscoveredPage]:
        self.calls += 1
        time.sleep(self.delay_seconds)
        return [
            DiscoveredPage(
                url=f"https://example.test/{query.replace(chr(32), chr(45))}",
                title=query,
                snippet=f"Result for {query}",
                source_name="benchmark",
            )
        ][:limit]


def benchmark_request(discovery: WebDiscovery, request: SearchRequest, iterations: int):
    samples = []

    for _ in range(iterations):
        started = time.perf_counter()
        discovery.discover(request)
        samples.append((time.perf_counter() - started) * 1000)

    return {
        "iterations": iterations,
        "mean_ms": statistics.mean(samples),
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def benchmark_cached(
    request: SearchRequest,
    iterations: int,
):
    with tempfile.TemporaryDirectory(prefix="discovery-cache-benchmark-") as tmp:
        database_path = Path(tmp) / "discovery.duckdb"
        provider = CountingProvider()
        cache = DiscoveryCache(database_path)
        discovery = WebDiscovery(
            providers=[provider],
            cache=cache,
        )

        samples = []
        misses = 0

        for iteration in range(iterations):
            started = time.perf_counter()
            discovery.discover(request)
            samples.append((time.perf_counter() - started) * 1000)

            if iteration == 0:
                misses += 1

        hits = iterations - misses
        database_size_bytes = database_path.stat().st_size

        return {
            "iterations": iterations,
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / iterations,
            "mean_ms": statistics.mean(samples),
            "median_ms": statistics.median(samples),
            "min_ms": min(samples),
            "max_ms": max(samples),
            "provider_calls": provider.calls,
            "database_size_bytes": database_size_bytes,
        }


def run() -> dict:
    iterations = 20

    baseline_provider = CountingProvider()
    baseline_discovery = WebDiscovery(providers=[baseline_provider])

    request = SearchRequest(
        keyword="software company",
        location="Lucknow",
        requirements="contact",
        limit=5,
    )

    baseline = benchmark_request(
        baseline_discovery,
        request,
        iterations=iterations,
    )

    cached = benchmark_cached(
        request,
        iterations=iterations,
    )

    result = {
        "benchmark": "discovery-cache-benefit",
        "workload": {
            "keyword": request.keyword,
            "location": request.location,
            "requirements": request.requirements,
            "limit": request.limit,
        },
        "provider": {
            "delay_ms": CountingProvider.delay_seconds * 1000,
            "baseline_calls": baseline_provider.calls,
            "cached_calls": cached["provider_calls"],
        },
        "baseline": baseline,
        "cached": cached,
        "speedup": baseline["mean_ms"] / cached["mean_ms"],
        "provider_call_reduction": (
            1 - cached["provider_calls"] / baseline_provider.calls
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "baseline.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
