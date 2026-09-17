import threading
import time

import pytest

from scraper.concurrency import BoundedExecutor, DomainConcurrencyLimiter


def test_bounded_executor_limits_active_workers():
    active = 0
    maximum = 0
    lock = threading.Lock()

    def work(value):
        nonlocal active, maximum

        with lock:
            active += 1
            maximum = max(maximum, active)

        time.sleep(0.03)

        with lock:
            active -= 1

        return value * 2

    executor = BoundedExecutor(max_concurrency=2)

    try:
        results = executor.map(work, range(8))
    finally:
        executor.shutdown()

    assert results == [0, 2, 4, 6, 8, 10, 12, 14]
    assert maximum <= 2
    assert maximum == 2


def test_bounded_executor_preserves_input_order():
    def work(value):
        time.sleep(0.01 * (5 - value))
        return value

    executor = BoundedExecutor(max_concurrency=3)

    try:
        results = executor.map(work, range(5))
    finally:
        executor.shutdown()

    assert results == [0, 1, 2, 3, 4]


@pytest.mark.parametrize("limit", [0, -1])
def test_bounded_executor_rejects_non_positive_limit(limit):
    with pytest.raises(ValueError, match="max_concurrency"):
        BoundedExecutor(max_concurrency=limit)


def test_bounded_executor_rejects_non_integer_limit():
    with pytest.raises(ValueError, match="max_concurrency"):
        BoundedExecutor(max_concurrency=1.5)


def test_bounded_executor_map_isolated_preserves_order_and_failures():
    def work(value):
        if value == 2:
            raise RuntimeError("boom")
        return value * 2

    executor = BoundedExecutor(max_concurrency=2)

    try:
        results = executor.map_isolated(work, range(5))
    finally:
        executor.shutdown()

    assert [item.input for item in results] == [0, 1, 2, 3, 4]
    assert [item.result for item in results] == [0, 2, None, 6, 8]
    assert [item.ok for item in results] == [True, True, False, True, True]
    assert isinstance(results[2].error, RuntimeError)
    assert str(results[2].error) == "boom"


def test_bounded_executor_map_isolated_limits_active_workers():
    active = 0
    maximum = 0
    lock = threading.Lock()

    def work(value):
        nonlocal active, maximum

        with lock:
            active += 1
            maximum = max(maximum, active)

        time.sleep(0.03)

        with lock:
            active -= 1

        return value

    executor = BoundedExecutor(max_concurrency=2)

    try:
        results = executor.map_isolated(work, range(8))
    finally:
        executor.shutdown()

    assert [item.result for item in results] == list(range(8))
    assert maximum == 2


def test_bounded_executor_map_isolated_enforces_domain_limit():
    from urllib.parse import urlparse

    active_by_domain = {}
    maximum_by_domain = {}
    lock = threading.Lock()

    def work(url):
        domain = urlparse(url).netloc

        with lock:
            active_by_domain[domain] = active_by_domain.get(domain, 0) + 1
            maximum_by_domain[domain] = max(
                maximum_by_domain.get(domain, 0),
                active_by_domain[domain],
            )

        time.sleep(0.03)

        with lock:
            active_by_domain[domain] -= 1

        return url

    urls = [
        "https://one.example/a",
        "https://one.example/b",
        "https://one.example/c",
        "https://two.example/a",
        "https://two.example/b",
        "https://two.example/c",
    ]

    executor = BoundedExecutor(max_concurrency=4)
    limiter = DomainConcurrencyLimiter(max_concurrency=2)

    try:
        results = executor.map_isolated(
            work,
            urls,
            domain_limiter=limiter,
            domain_key=lambda url: urlparse(url).netloc.lower(),
        )
    finally:
        executor.shutdown()

    assert [item.result for item in results] == urls
    assert maximum_by_domain["one.example"] == 2
    assert maximum_by_domain["two.example"] == 2


def test_bounded_executor_map_isolated_allows_independent_domains():
    from urllib.parse import urlparse

    active = 0
    maximum = 0
    lock = threading.Lock()

    def work(url):
        nonlocal active, maximum

        with lock:
            active += 1
            maximum = max(maximum, active)

        time.sleep(0.04)

        with lock:
            active -= 1

        return url

    urls = [
        "https://one.example/a",
        "https://one.example/b",
        "https://two.example/a",
        "https://two.example/b",
    ]

    executor = BoundedExecutor(max_concurrency=4)
    limiter = DomainConcurrencyLimiter(max_concurrency=1)

    try:
        results = executor.map_isolated(
            work,
            urls,
            domain_limiter=limiter,
            domain_key=lambda url: urlparse(url).netloc.lower(),
        )
    finally:
        executor.shutdown()

    assert [item.result for item in results] == urls
    assert maximum == 2


def test_bounded_executor_map_isolated_rejects_domain_limiter_without_key():
    executor = BoundedExecutor(max_concurrency=2)
    limiter = DomainConcurrencyLimiter(max_concurrency=1)

    try:
        with pytest.raises(ValueError, match="domain_key"):
            executor.map_isolated(
                lambda value: value,
                [1],
                domain_limiter=limiter,
            )
    finally:
        executor.shutdown()


def test_bounded_executor_map_isolated_handles_empty_batch():
    executor = BoundedExecutor(max_concurrency=2)

    try:
        results = executor.map_isolated(lambda value: value, [])
    finally:
        executor.shutdown()

    assert results == []
