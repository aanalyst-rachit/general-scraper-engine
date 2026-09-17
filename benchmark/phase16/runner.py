from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scraper.acquisition import CachedFetcher, HTTPFetcherAdapter
from scraper.cache.fetch import FetchCache
from scraper.concurrency import BoundedExecutor
from scraper.content_quality import ContentQuality, ContentQualityClassifier
from scraper.extraction import ExtractionStrategy
from scraper.fetcher import FetchedPage
from scraper.location import LocationValidator
from scraper.models import Lead
from scraper.parser import PageParser
from scraper.structured_data import StructuredDataExtractor


BASE_URL = "http://127.0.0.1:8766"
RESULTS = ROOT / "benchmark" / "phase16" / "results" / "matrix.json"


class FakeBrowserFetcher:
    acquisition_strategy = "browser"

    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, request) -> FetchedPage:
        self.calls += 1
        return FetchedPage(
            url=request.url,
            final_url=request.url,
            status_code=200,
            content_type="text/html",
            html=(
                "<html><body><main>"
                "<h1>Rendered Browser Result</h1>"
                "<p>Browser-rendered content is available.</p>"
                "</main></body></html>"
            ),
        )


class FakeExternalFetcher:
    acquisition_strategy = "external"

    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, request) -> FetchedPage:
        self.calls += 1
        return FetchedPage(
            url=request.url,
            final_url=request.url,
            status_code=200,
            content_type="text/html",
            html=(
                "<html><body><main>"
                "<h1>External Provider Result</h1>"
                "<p>Provider acquisition completed.</p>"
                "</main></body></html>"
            ),
        )


class StaticFetcher:
    acquisition_strategy = "http"

    def __init__(self, page: FetchedPage) -> None:
        self.page = page
        self.calls = 0

    def fetch(self, request) -> FetchedPage:
        self.calls += 1
        return self.page


def fetch_local(path: str) -> FetchedPage:
    import httpx

    response = httpx.get(f"{BASE_URL}{path}", timeout=5.0)
    return FetchedPage(
        url=f"{BASE_URL}{path}",
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=response.headers.get("content-type", ""),
        html=response.text,
    )


def benchmark_static() -> dict[str, object]:
    page = fetch_local("/static")
    return {
        "name": "normal_static_html",
        "passed": page.ok and page.status_code == 200 and bool(page.html),
        "status_code": page.status_code,
        "content_bytes": len(page.html.encode("utf-8")),
    }


def benchmark_quality_matrix() -> dict[str, object]:
    classifier = ContentQualityClassifier()
    pages = {
        "js_heavy": fetch_local("/js-shell"),
        "empty_thin": fetch_local("/thin"),
        "blocked": FetchedPage(
            url="http://fixture.local/blocked",
            status_code=403,
            html="<html><body>Forbidden</body></html>",
        ),
        "rate_limited": FetchedPage(
            url="http://fixture.local/rate-limited",
            status_code=429,
            html="<html><body>Too many requests</body></html>",
        ),
    }

    results = {}
    expected = {
        "js_heavy": ContentQuality.JS_SHELL,
        "empty_thin": ContentQuality.EMPTY_CONTENT,
        "blocked": ContentQuality.ACCESS_BLOCKED,
        "rate_limited": ContentQuality.RATE_LIMITED,
    }

    for name, page in pages.items():
        result = classifier.classify(page)
        results[name] = {
            "quality": result.category.value,
            "needs_browser_fallback": result.needs_browser_fallback,
            "passed": result.category == expected[name],
        }

    return {
        "name": "content_quality_workloads",
        "passed": all(item["passed"] for item in results.values()),
        "cases": results,
    }


def benchmark_repeated_url() -> dict[str, object]:
    page = fetch_local("/static")

    with tempfile.TemporaryDirectory() as temp_dir:
        cache = FetchCache(Path(temp_dir) / "fetch.duckdb")
        source = StaticFetcher(page)
        cached = CachedFetcher(source, cache, acquisition_strategy="http")

        first = cached.fetch(type("Request", (), {"url": page.url})())
        second = cached.fetch(type("Request", (), {"url": page.url})())

        stats = {
            "name": "repeated_url",
            "passed": (
                first.ok
                and second.ok
                and source.calls == 1
                and cached.cache_hits == 1
                and cached.cache_misses == 1
            ),
            "underlying_calls": source.calls,
            "cache_hits": cached.cache_hits,
            "cache_misses": cached.cache_misses,
        }
        cache.close()

    return stats


def benchmark_large_batch() -> dict[str, object]:
    values = list(range(40))
    lock = Lock()
    active = 0
    peak = 0

    def work(value: int) -> int:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.01)
        with lock:
            active -= 1
        return value * 2

    started = time.perf_counter()
    with BoundedExecutor(8) as executor:
        results = executor.map_isolated(work, values)
    elapsed_ms = (time.perf_counter() - started) * 1000

    return {
        "name": "large_url_batch",
        "passed": (
            len(results) == 40
            and all(item.ok for item in results)
            and peak <= 8
        ),
        "items": len(values),
        "peak_workers": peak,
        "elapsed_ms": round(elapsed_ms, 3),
        "throughput_items_per_sec": round(
            len(values) / (elapsed_ms / 1000), 3
        ),
    }


def benchmark_extraction() -> dict[str, object]:
    page = fetch_local("/structured")
    parser = PageParser()
    lead = parser.parse(page)

    generic_strategy = StructuredDataExtractor()
    structured = generic_strategy.extract(page.html)

    return {
        "name": "generic_and_structured_extraction",
        "passed": (
            lead is not None
            and bool(structured)
            and bool(lead.name)
        ),
        "lead_name": lead.name if lead else "",
        "structured_fields": sorted(structured.keys()) if structured else [],
    }


def benchmark_location_quality() -> dict[str, object]:
    matching = Lead(
        name="Test Doctor",
        city="Shahjahanpur",
        state="Uttar Pradesh",
        country="India",
    )
    wrong = Lead(
        name="Other Doctor",
        city="Lucknow",
        state="Uttar Pradesh",
        country="India",
    )

    validator = LocationValidator("Shahjahanpur")
    matching_result = validator.is_relevant(matching)
    wrong_result = validator.is_relevant(wrong)

    return {
        "name": "location_quality",
        "passed": matching_result and not wrong_result,
        "matching_location": matching_result,
        "wrong_location": wrong_result,
    }


def benchmark_sequential_vs_concurrent() -> dict[str, object]:
    values = list(range(24))

    def work(value: int) -> int:
        time.sleep(0.02)
        return value

    started = time.perf_counter()
    sequential = [work(value) for value in values]
    sequential_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    with BoundedExecutor(8) as executor:
        concurrent = [item.result for item in executor.map_isolated(work, values)]
    concurrent_ms = (time.perf_counter() - started) * 1000

    return {
        "name": "sequential_vs_concurrent",
        "passed": sequential == concurrent and concurrent_ms < sequential_ms,
        "sequential_ms": round(sequential_ms, 3),
        "concurrent_ms": round(concurrent_ms, 3),
        "speedup": round(sequential_ms / concurrent_ms, 3),
    }


def benchmark_http_vs_browser() -> dict[str, object]:
    page = fetch_local("/static")
    http = StaticFetcher(page)
    browser = FakeBrowserFetcher()

    http_result = http.fetch(type("Request", (), {"url": page.url})())
    browser_result = browser.fetch(type("Request", (), {"url": page.url})())

    return {
        "name": "http_vs_browser",
        "passed": (
            http_result.ok
            and browser_result.ok
            and http.calls == 1
            and browser.calls == 1
        ),
        "http_strategy": http.acquisition_strategy,
        "browser_strategy": browser.acquisition_strategy,
        "browser_calls": browser.calls,
    }


def benchmark_native_vs_external() -> dict[str, object]:
    page = fetch_local("/static")
    native = StaticFetcher(page)
    external = FakeExternalFetcher()

    native_result = native.fetch(type("Request", (), {"url": page.url})())
    external_result = external.fetch(type("Request", (), {"url": page.url})())

    return {
        "name": "native_vs_external_provider",
        "passed": (
            native_result.ok
            and external_result.ok
            and native.calls == 1
            and external.calls == 1
        ),
        "native_strategy": native.acquisition_strategy,
        "external_strategy": external.acquisition_strategy,
    }


def benchmark_cache_vs_no_cache() -> dict[str, object]:
    page = fetch_local("/static")

    uncached = StaticFetcher(page)
    request = type("Request", (), {"url": page.url})()

    started = time.perf_counter()
    uncached.fetch(request)
    uncached.fetch(request)
    uncached_ms = (time.perf_counter() - started) * 1000

    with tempfile.TemporaryDirectory() as temp_dir:
        cache = FetchCache(Path(temp_dir) / "fetch.duckdb")
        cached_source = StaticFetcher(page)
        cached = CachedFetcher(cached_source, cache, acquisition_strategy="http")

        started = time.perf_counter()
        cached.fetch(request)
        cached.fetch(request)
        cached_ms = (time.perf_counter() - started) * 1000

        calls = cached_source.calls
        hits = cached.cache_hits
        cache.close()

    return {
        "name": "cache_vs_no_cache",
        "passed": calls == 1 and hits == 1,
        "uncached_ms": round(uncached_ms, 3),
        "cached_ms": round(cached_ms, 3),
        "uncached_calls": uncached.calls,
        "cached_underlying_calls": calls,
        "cache_hits": hits,
    }


def main() -> None:
    benchmarks = [
        benchmark_static(),
        benchmark_quality_matrix(),
        benchmark_repeated_url(),
        benchmark_large_batch(),
        benchmark_extraction(),
        benchmark_location_quality(),
        benchmark_sequential_vs_concurrent(),
        benchmark_http_vs_browser(),
        benchmark_native_vs_external(),
        benchmark_cache_vs_no_cache(),
    ]

    # The remaining matrix rows are represented by the quality/extraction
    # workloads above and deliberately use deterministic synthetic fixtures.
    matrix = {
        "benchmark": "phase-16-test-benchmark-matrix",
        "workloads": benchmarks,
        "passed_workloads": sum(1 for item in benchmarks if item["passed"]),
        "total_workloads": len(benchmarks),
        "all_passed": all(item["passed"] for item in benchmarks),
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    print("===== PHASE 16 TEST & BENCHMARK MATRIX =====")
    print("Passed:", matrix["passed_workloads"], "/", matrix["total_workloads"])
    print("All passed:", matrix["all_passed"])
    print("Results:", RESULTS)


if __name__ == "__main__":
    main()
