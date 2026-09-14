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
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self._robots: dict[str, RobotFileParser] = {}
        self._robots_errors: dict[str, str] = {}
        self._last_request_at: dict[str, float] = {}

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

    def _wait_for_crawl_delay(self, url: str) -> None:
        delay = self._crawl_delay_for(url)
        if delay is None or delay <= 0:
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

    def _allowed(self, url: str) -> bool:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        if not parsed.netloc:
            return False

        parser = self._robots_for(url)
        return parser.can_fetch(self.user_agent, url)

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

        self._wait_for_crawl_delay(url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)

            content_type = response.headers.get("content-type", "")

            if response.status_code >= 400:
                return FetchedPage(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=content_type,
                    error=f"HTTP {response.status_code}",
                )

            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
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
            return FetchedPage(url=url, error="request timeout")
        except httpx.HTTPError as exc:
            return FetchedPage(url=url, error=f"HTTP error: {exc}")
        except Exception as exc:
            return FetchedPage(url=url, error=f"fetch error: {exc}")
