import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


@dataclass(frozen=True)
class FetchedPage:
    url: str
    final_url: str = ""
    status_code: int = 0
    content_type: str = ""
    html: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and bool(self.html)


class PageFetcher:
    def __init__(
        self,
        timeout: float = 15.0,
        user_agent: str = "GeneralScraperEngine/0.1 (+public-web-fetcher)",
        request_delay: float = 0.0,
        max_requests_per_domain: int | None = None,
        max_retries: int = 0,
        retry_backoff: float = 0.0,
    ):
        self.timeout = timeout
        self.request_delay = max(0.0, float(request_delay))
        if max_requests_per_domain is not None and max_requests_per_domain < 0:
            raise ValueError("max_requests_per_domain must be >= 0 or None")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if retry_backoff < 0:
            raise ValueError("retry_backoff must be >= 0")
        self.max_requests_per_domain = max_requests_per_domain
        self.max_retries = int(max_retries)
        self.retry_backoff = float(retry_backoff)
        self.user_agent = user_agent
        self._robots: dict[str, RobotFileParser] = {}
        self._robots_errors: dict[str, str] = {}
        self._last_request_at: dict[str, float] = {}
        self._domain_request_counts: dict[str, int] = {}

    def _robots_for(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        if robots_url in self._robots_errors:
            raise RuntimeError(self._robots_errors[robots_url])

        if robots_url in self._robots:
            return self._robots[robots_url]

        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            parser.read()
        except Exception as exc:
            error = f"robots.txt unavailable: {exc}"
            self._robots_errors[robots_url] = error
            raise RuntimeError(error) from exc

        self._robots[robots_url] = parser
        return parser

    def _crawl_delay_for(self, url: str) -> float | None:
        parser = self._robots_for(url)
        delay = parser.crawl_delay(self.user_agent)
        if delay is None:
            return None
        try:
            delay = float(delay)
        except (TypeError, ValueError):
            return None
        return max(0.0, delay)

    def _wait_for_request_delay(self, url: str) -> None:
        crawl_delay = self._crawl_delay_for(url)
        delay = max(self.request_delay, crawl_delay or 0.0)
        if delay <= 0:
            return

        parsed = urlparse(url)
        origin = f'{parsed.scheme}://{parsed.netloc}'
        now = time.monotonic()
        last_request = self._last_request_at.get(origin)

        if last_request is not None:
            remaining = delay - (now - last_request)
            if remaining > 0:
                time.sleep(remaining)
                now = time.monotonic()

        self._last_request_at[origin] = now

    def _wait_for_crawl_delay(self, url: str) -> None:
        self._wait_for_request_delay(url)

    def _allowed(self, url: str) -> bool:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        if not parsed.netloc:
            return False

        parser = self._robots_for(url)
        return parser.can_fetch(self.user_agent, url)

    def _domain_for(self, url: str) -> str:
        return urlparse(url).netloc

    def _domain_limit_reached(self, url: str) -> bool:
        if self.max_requests_per_domain is None:
            return False

        domain = self._domain_for(url)
        return self._domain_request_counts.get(domain, 0) >= self.max_requests_per_domain

    def _record_domain_request(self, url: str) -> None:
        domain = self._domain_for(url)
        self._domain_request_counts[domain] = (
            self._domain_request_counts.get(domain, 0) + 1
        )

    def fetch(self, url: str) -> FetchedPage:
        url = url.strip()

        if not url:
            return FetchedPage(url=url, error="empty URL")

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return FetchedPage(url=url, error="unsupported URL")

        try:
            if not self._allowed(url):
                return FetchedPage(url=url, error="blocked by robots.txt")
        except Exception as exc:
            return FetchedPage(url=url, error=f"robots check failed: {exc}")

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            last_retryable_result: FetchedPage | None = None

            for attempt in range(self.max_retries + 1):
                if self._domain_limit_reached(url):
                    if last_retryable_result is not None:
                        return last_retryable_result
                    return FetchedPage(
                        url=url,
                        error="per-domain request limit reached",
                    )

                self._record_domain_request(url)
                self._wait_for_request_delay(url)

                try:
                    response = client.get(url)
                    content_type = response.headers.get("content-type", "")

                    if response.status_code >= 400:
                        result = FetchedPage(
                            url=url,
                            final_url=str(response.url),
                            status_code=response.status_code,
                            content_type=content_type,
                            error=f"HTTP {response.status_code}",
                        )

                        if response.status_code < 500:
                            return result

                        last_retryable_result = result

                        if attempt >= self.max_retries:
                            return result

                        if self.retry_backoff > 0:
                            time.sleep(self.retry_backoff * (attempt + 1))
                        continue

                    if (
                        "text/html" not in content_type
                        and "application/xhtml+xml" not in content_type
                    ):
                        return FetchedPage(
                            url=url,
                            final_url=str(response.url),
                            status_code=response.status_code,
                            content_type=content_type,
                            error="not an HTML page",
                        )

                    return FetchedPage(
                        url=url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=content_type,
                        html=response.text,
                    )

                except httpx.TimeoutException:
                    last_retryable_result = FetchedPage(
                        url=url,
                        error="request timeout",
                    )

                    if attempt >= self.max_retries:
                        return last_retryable_result

                    if self.retry_backoff > 0:
                        time.sleep(self.retry_backoff * (attempt + 1))

                except httpx.HTTPError as exc:
                    last_retryable_result = FetchedPage(
                        url=url,
                        error=f"HTTP error: {exc}",
                    )

                    if attempt >= self.max_retries:
                        return last_retryable_result

                    if self.retry_backoff > 0:
                        time.sleep(self.retry_backoff * (attempt + 1))

                except Exception as exc:
                    return FetchedPage(
                        url=url,
                        error=f"fetch error: {exc}",
                    )
