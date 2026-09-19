from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator


class ImageEngineBrowser:
    def __init__(
        self,
        browser_factory: Callable[[], object],
        *,
        timeout: float = 15.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.browser_factory = browser_factory
        self.timeout = float(timeout)

    @contextmanager
    def session(self) -> Iterator[object]:
        with self.browser_factory() as playwright:
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout * 1000)
                yield page
            finally:
                browser.close()


def default_browser_factory() -> object:
    from playwright.sync_api import sync_playwright

    return sync_playwright()
