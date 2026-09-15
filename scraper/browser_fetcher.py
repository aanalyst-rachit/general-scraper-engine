from __future__ import annotations

from dataclasses import dataclass
from threading import BoundedSemaphore
from typing import Callable
from urllib.parse import urlparse

from scraper.acquisition import AcquisitionStrategy, FetchRequest
from scraper.fetcher import FetchedPage


@dataclass(frozen=True)
class BrowserFetchOptions:
    timeout: float = 15.0
    wait_for_timeout: float = 0.0
    wait_for_selector: str | None = None
    scroll_steps: int = 0
    click_selector: str | None = None
    max_concurrency: int = 2


class BrowserFetcher:
    def __init__(
        self,
        timeout: float = 15.0,
        wait_for_timeout: float = 0.0,
        wait_for_selector: str | None = None,
        scroll_steps: int = 0,
        click_selector: str | None = None,
        max_concurrency: int = 2,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")
        if wait_for_timeout < 0:
            raise ValueError("wait_for_timeout must be >= 0")
        if scroll_steps < 0:
            raise ValueError("scroll_steps must be >= 0")
        if click_selector == "":
            raise ValueError("click_selector must be non-empty or None")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be > 0")

        self.options = BrowserFetchOptions(
            timeout=float(timeout),
            wait_for_timeout=float(wait_for_timeout),
            wait_for_selector=wait_for_selector,
            scroll_steps=int(scroll_steps),
            click_selector=click_selector,
            max_concurrency=int(max_concurrency),
        )
        self._playwright_factory = playwright_factory
        self._concurrency = BoundedSemaphore(self.options.max_concurrency)

    def fetch(self, request: FetchRequest) -> FetchedPage:
        url = request.url.strip()

        if not url:
            return FetchedPage(url=url, error="empty URL")

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return FetchedPage(url=url, error="unsupported URL")

        try:
            with self._concurrency:
                return self._fetch_with_browser(request, url)
        except ModuleNotFoundError as exc:
            return FetchedPage(
                url=url,
                error=f"Playwright unavailable: {exc}",
            )
        except Exception as exc:
            return FetchedPage(
                url=url,
                error=f"browser fetch error: {exc}",
            )

    def _fetch_with_browser(
        self,
        request: FetchRequest,
        url: str,
    ) -> FetchedPage:
        with self._playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            try:
                page = browser.new_page()
                page.set_default_timeout(self.options.timeout * 1000)
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.options.timeout * 1000,
                )
                if self.options.wait_for_timeout > 0:
                    page.wait_for_timeout(
                        self.options.wait_for_timeout * 1000
                    )
                if self.options.wait_for_selector is not None:
                    page.wait_for_selector(
                        self.options.wait_for_selector,
                        timeout=self.options.timeout * 1000,
                    )
                if self.options.click_selector is not None:
                    page.locator(self.options.click_selector).click()
                for _ in range(self.options.scroll_steps):
                    page.evaluate(
                        "() => window.scrollBy(0, window.innerHeight)"
                    )
                    page.wait_for_timeout(50)

                html = page.content()
                final_url = page.url
                status_code = (
                    response.status if response is not None else 200
                )
                content_type = (
                    response.headers.get("content-type", "")
                    if response is not None
                    else "text/html"
                )
                return FetchedPage(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    content_type=content_type,
                    html=html,
                )
            finally:
                browser.close()

    def _playwright(self):
        if self._playwright_factory is not None:
            return self._playwright_factory()

        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError:
            raise

        return sync_playwright()
