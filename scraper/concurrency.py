from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class ConcurrencyConfig:
    """
    Formal concurrency limits for the scraper engine.

    - global_limit: maximum number of concurrent fetch tasks across the whole run.
    - per_domain_limit: maximum concurrent requests to the same domain (Phase 4.3).
    - provider_limit: maximum concurrent requests per acquisition provider (Phase 4.4).
    """

    global_limit: int = 4
    per_domain_limit: int | None = None
    provider_limit: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.global_limit, bool) or not isinstance(self.global_limit, int):
            raise ValueError("global_limit must be a positive integer")
        if self.global_limit <= 0:
            raise ValueError("global_limit must be a positive integer")

        if self.per_domain_limit is not None:
            if isinstance(self.per_domain_limit, bool) or not isinstance(self.per_domain_limit, int):
                raise ValueError("per_domain_limit must be a positive integer or None")
            if self.per_domain_limit <= 0:
                raise ValueError("per_domain_limit must be a positive integer or None")

        if self.provider_limit is not None:
            if isinstance(self.provider_limit, bool) or not isinstance(self.provider_limit, int):
                raise ValueError("provider_limit must be a positive integer or None")
            if self.provider_limit <= 0:
                raise ValueError("provider_limit must be a positive integer or None")


class BoundedExecutor:
    """
    Hard-bounded concurrent executor.

    Guarantees that at most `max_concurrency` tasks run at the same time.
    Never creates unbounded tasks.
    """

    def __init__(self, max_concurrency: int) -> None:
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int):
            raise ValueError("max_concurrency must be a positive integer")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be a positive integer")

        self.max_concurrency = max_concurrency
        self._executor = ThreadPoolExecutor(max_workers=max_concurrency)
        self._shutdown = False

    def map(
        self,
        function: Callable[[T], R],
        values: Iterable[T],
    ) -> list[R]:
        if self._shutdown:
            raise RuntimeError("executor has been shut down")

        iterator = iter(values)
        pending: list[Future[R]] = []

        # Fill up to the concurrency limit
        for _ in range(self.max_concurrency):
            try:
                value = next(iterator)
            except StopIteration:
                break
            pending.append(self._executor.submit(function, value))

        results: list[R] = []
        while pending:
            future = pending.pop(0)
            results.append(future.result())

            try:
                value = next(iterator)
            except StopIteration:
                continue
            pending.append(self._executor.submit(function, value))

        return results

    def shutdown(self, wait: bool = True) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._executor.shutdown(wait=wait)

    def __enter__(self) -> BoundedExecutor:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.shutdown()


class DomainConcurrencyLimiter:
    """Limits simultaneously active operations per network domain."""

    def __init__(self, max_concurrency: int) -> None:
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int):
            raise ValueError("max_concurrency must be a positive integer")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be a positive integer")

        from collections import defaultdict
        from threading import BoundedSemaphore, Lock

        self.max_concurrency = max_concurrency
        self._semaphores = defaultdict(lambda: BoundedSemaphore(max_concurrency))
        self._lock = Lock()

    def _semaphore_for(self, domain: str):
        with self._lock:
            return self._semaphores[domain]

    def acquire(self, domain: str):
        semaphore = self._semaphore_for(domain)
        semaphore.acquire()
        return semaphore
