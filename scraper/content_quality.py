from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from bs4 import BeautifulSoup

from scraper.fetcher import FetchedPage


class ContentQuality(str, Enum):
    VALID_CONTENT = "valid_content"
    EMPTY_CONTENT = "empty_content"
    THIN_CONTENT = "thin_content"
    JS_SHELL = "js_shell"
    ERROR_PAGE = "error_page"
    BLOCK_PAGE = "block_page"


@dataclass(frozen=True)
class ContentQualityResult:
    category: ContentQuality
    reason: str

    @property
    def needs_browser_fallback(self) -> bool:
        return self.category in {
            ContentQuality.EMPTY_CONTENT,
            ContentQuality.THIN_CONTENT,
            ContentQuality.JS_SHELL,
        }


class ContentQualityClassifier:
    _ERROR_MARKERS = (
        "internal server error",
        "server error",
        "page not found",
        "404 not found",
        "bad gateway",
        "service unavailable",
    )

    _BLOCK_MARKERS = (
        "access denied",
        "verify you are human",
        "captcha",
        "cloudflare",
        "bot detection",
        "security check",
        "request blocked",
    )

    _SHELL_IDS = {"root", "app", "__next", "__nuxt"}
    _MIN_BODY_TEXT = 24

    _USEFUL_JSON_LD_TYPES = {
        "person",
        "organization",
        "localbusiness",
        "professionalservice",
        "medicalbusiness",
        "physician",
        "dentist",
        "restaurant",
        "store",
        "educationalorganization",
        "realestateagent",
    }

    def classify(self, page: FetchedPage) -> ContentQualityResult:
        if page.status_code >= 400:
            return ContentQualityResult(
                ContentQuality.ERROR_PAGE,
                f"HTTP {page.status_code}",
            )

        if not page.html.strip():
            return ContentQualityResult(
                ContentQuality.EMPTY_CONTENT,
                "empty HTML",
            )

        soup = BeautifulSoup(page.html, "lxml")
        title = (
            soup.title.get_text(" ", strip=True).lower()
            if soup.title
            else ""
        )
        headings = " ".join(
            tag.get_text(" ", strip=True).lower()
            for tag in soup.find_all(["h1", "h2", "h3"])
        )
        has_external_script = bool(soup.find("script", src=True))

        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        body_text = (
            soup.body.get_text(" ", strip=True)
            if soup.body
            else ""
        )
        text = f"{title} {body_text}".lower()

        if any(marker in text for marker in self._BLOCK_MARKERS):
            return ContentQualityResult(
                ContentQuality.BLOCK_PAGE,
                "block/challenge marker detected",
            )

        error_signal = f"{title} {headings}"
        if any(marker in error_signal for marker in self._ERROR_MARKERS):
            return ContentQualityResult(
                ContentQuality.ERROR_PAGE,
                "error-page marker detected",
            )

        if self._has_entity_json_ld(page.html):
            return ContentQualityResult(
                ContentQuality.VALID_CONTENT,
                "entity JSON-LD detected",
            )

        if self._looks_like_js_shell(
            soup,
            body_text,
            has_external_script,
        ):
            return ContentQualityResult(
                ContentQuality.JS_SHELL,
                "shell container with insufficient rendered text",
            )

        if not body_text:
            return ContentQualityResult(
                ContentQuality.EMPTY_CONTENT,
                "HTML body has no text",
            )

        if len(body_text) < self._MIN_BODY_TEXT:
            return ContentQualityResult(
                ContentQuality.THIN_CONTENT,
                "insufficient rendered body text",
            )

        return ContentQualityResult(
            ContentQuality.VALID_CONTENT,
            "sufficient rendered body content",
        )

    def _has_entity_json_ld(self, html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")

        for script in soup.find_all(
            "script",
            attrs={"type": "application/ld+json"},
        ):
            raw = script.string or script.get_text()
            if not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = data if isinstance(data, list) else [data]

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                nodes = [item]
                graph = item.get("@graph")
                if isinstance(graph, list):
                    nodes.extend(
                        node
                        for node in graph
                        if isinstance(node, dict)
                    )

                for node in nodes:
                    entity_type = node.get("@type", "")

                    if isinstance(entity_type, list):
                        entity_types = {
                            str(value).lower()
                            for value in entity_type
                        }
                    else:
                        entity_types = {str(entity_type).lower()}

                    if (
                        entity_types & self._USEFUL_JSON_LD_TYPES
                        and node.get("name")
                    ):
                        return True

        return False

    def _looks_like_js_shell(
        self,
        soup: BeautifulSoup,
        body_text: str,
        has_external_script: bool,
    ) -> bool:
        if len(body_text) >= self._MIN_BODY_TEXT:
            return False

        has_mount = any(
            soup.find(id=value) is not None
            for value in self._SHELL_IDS
        )

        return has_mount and has_external_script
