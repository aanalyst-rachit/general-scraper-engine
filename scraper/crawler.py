from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fnmatch import fnmatch
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from scraper.acquisition import AcquisitionStrategy, FetchRequest
from scraper.concurrency import BoundedExecutor, ConcurrencyConfig, DomainConcurrencyLimiter
from scraper.fetcher import FetchedPage


@dataclass(frozen=True)
class CrawlPage:
    url: str
    depth: int
    page: FetchedPage


@dataclass(frozen=True)
class CrawlResult:
    pages: list[CrawlPage]
    discovered_urls: list[str]

    @property
    def count(self) -> int:
        return len(self.pages)


class SiteCrawler:
    """Bounded same-site crawler built on the existing acquisition layer."""

    def __init__(
        self,
        acquisition: AcquisitionStrategy,
        *,
        max_pages: int = 10,
        max_depth: int = 1,
        allowed_domains: set[str] | None = None,
        include_patterns: tuple[str, ...] = (),
        exclude_patterns: tuple[str, ...] = (),
        concurrency: ConcurrencyConfig | None = None,
    ) -> None:
        if max_pages <= 0:
            raise ValueError("max_pages must be positive")
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")

        self.acquisition = acquisition
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.concurrency = concurrency or ConcurrencyConfig(global_limit=1)
        self.allowed_domains = {
            self._normalize_domain(domain)
            for domain in (allowed_domains or set())
            if self._normalize_domain(domain)
        }
        self.include_patterns = tuple(include_patterns)
        self.exclude_patterns = tuple(exclude_patterns)

    def crawl(self, seed_url: str) -> CrawlResult:
        seed = self.canonicalize_url(seed_url)
        if not seed:
            return CrawlResult(pages=[], discovered_urls=[])

        queue: deque[tuple[str, int]] = deque([(seed, 0)])
        queued = {seed}
        visited: set[str] = set()
        pages: list[CrawlPage] = []
        discovered_urls: list[str] = []

        with BoundedExecutor(self.concurrency.global_limit) as executor:
            domain_limiter = (
                DomainConcurrencyLimiter(self.concurrency.per_domain_limit)
                if self.concurrency.per_domain_limit is not None
                else None
            )

            while queue and len(pages) < self.max_pages:
                frontier: list[tuple[str, int]] = []

                remaining_pages = self.max_pages - len(pages)
                while queue and len(frontier) < self.concurrency.global_limit:
                    url, depth = queue.popleft()

                    if url in visited:
                        continue
                    visited.add(url)

                    if not self._allowed_url(url, seed):
                        continue

                    # The seed may be fetched solely for link discovery when
                    # include patterns are active, so it does not consume the
                    # returned-page budget in that case.
                    counts_toward_budget = not (
                        url == seed and self.include_patterns
                    )

                    if counts_toward_budget and remaining_pages <= 0:
                        continue

                    frontier.append((url, depth))

                    if counts_toward_budget:
                        remaining_pages -= 1

                if not frontier:
                    continue

                fetches = executor.map(
                    lambda item: self._fetch(
                        item,
                        domain_limiter,
                    ),
                    frontier,
                )

                for (url, depth), page in zip(frontier, fetches):
                    discovered_urls.append(url)

                    if not page.ok:
                        continue

                    if not (url == seed and self.include_patterns):
                        pages.append(CrawlPage(url=url, depth=depth, page=page))

                    if depth >= self.max_depth:
                        continue

                    for child in self.extract_links(
                        page.html,
                        page.final_url or url,
                    ):
                        child = self.canonicalize_url(child)
                        if not child or child in queued:
                            continue
                        if not self._allowed_url(child, seed):
                            continue

                        queued.add(child)
                        queue.append((child, depth + 1))

        return CrawlResult(
            pages=pages,
            discovered_urls=discovered_urls,
        )

    def _fetch(
        self,
        item: tuple[str, int],
        domain_limiter: DomainConcurrencyLimiter | None = None,
    ) -> FetchedPage:
        url, _ = item
        semaphore = None

        try:
            if domain_limiter is not None:
                domain = urlsplit(url).netloc.lower()
                semaphore = domain_limiter.acquire(domain)

            return self.acquisition.fetch(FetchRequest(url))
        except Exception as exc:
            return FetchedPage(url=url, error=str(exc))
        finally:
            if semaphore is not None:
                semaphore.release()

    @classmethod
    def canonicalize_url(cls, url: str, base_url: str = "") -> str:
        value = url.strip()
        if not value:
            return ""

        absolute = urljoin(base_url, value)
        try:
            parts = urlsplit(absolute)
        except ValueError:
            return ""

        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return ""

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/") or "/",
                parts.query,
                "",
            )
        )

    @staticmethod
    def extract_links(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html or "", "html.parser")
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if href:
                links.append(urljoin(base_url, href))

        return links

    def _allowed_url(self, url: str, seed_url: str) -> bool:
        parts = urlsplit(url)
        domain = self._normalize_domain(parts.netloc)

        if self.allowed_domains:
            if domain not in self.allowed_domains:
                return False
        else:
            if domain != self._normalize_domain(urlsplit(seed_url).netloc):
                return False

        target = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))

        # The seed must always be fetchable so it can discover candidate URLs.
        if target == self.canonicalize_url(seed_url):
            return True

        if self.include_patterns and not any(
            fnmatch(target, pattern) for pattern in self.include_patterns
        ):
            return False

        if any(fnmatch(target, pattern) for pattern in self.exclude_patterns):
            return False

        return True

    @staticmethod
    def _normalize_domain(value: str) -> str:
        return value.strip().casefold().split(":", 1)[0]
