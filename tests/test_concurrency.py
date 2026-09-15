import threading
import time

import pytest

from scraper.concurrency import BoundedExecutor


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
