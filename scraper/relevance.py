from __future__ import annotations

import re

from scraper.discovery import DiscoveredPage


class _TokenRelevance:
    def __init__(self, value: str, threshold: int = 1) -> None:
        self.value = value.strip()
        if not self.value:
            raise ValueError("relevance value must not be empty")
        if threshold < 0:
            raise ValueError("threshold must not be negative")
        self.threshold = threshold
        self.tokens = self._tokenize(self.value)

    def score(self, page: DiscoveredPage) -> int:
        title_tokens = self._tokenize(page.title)
        snippet_tokens = self._tokenize(page.snippet)
        url_tokens = self._tokenize(page.url)

        score = 0
        if self._matches(title_tokens):
            score += 3
        if self._matches(snippet_tokens):
            score += 2
        if self._matches(url_tokens):
            score += 1
        return score

    def is_relevant(self, page: DiscoveredPage) -> bool:
        return self.score(page) >= self.threshold

    def _matches(self, tokens: set[str]) -> bool:
        for value_token in self.tokens:
            if value_token in tokens or f"{value_token}s" in tokens:
                return True
        return False

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))


class KeywordRelevance(_TokenRelevance):
    def __init__(self, keyword: str, threshold: int = 1) -> None:
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("keyword must not be empty")
        super().__init__(keyword, threshold)


class LocationRelevance(_TokenRelevance):
    def __init__(self, location: str, threshold: int = 1) -> None:
        location = location.strip()
        if not location:
            raise ValueError("location must not be empty")
        super().__init__(location, threshold)


class CategoryRelevance(_TokenRelevance):
    def __init__(self, category: str, threshold: int = 1) -> None:
        category = category.strip()
        if not category:
            raise ValueError("category must not be empty")
        super().__init__(category, threshold)


class RequirementsRelevance:
    def __init__(self, requirements: str) -> None:
        self.requirements = requirements.strip()
        if not self.requirements:
            raise ValueError("requirements must not be empty")
        self.tokens = self._tokenize(self.requirements)

    def score(self, page: DiscoveredPage) -> int:
        available = (
            self._tokenize(page.title)
            | self._tokenize(page.snippet)
            | self._tokenize(page.url)
        )
        return sum(1 for token in self.tokens if self._token_matches(token, available))

    def is_relevant(self, page: DiscoveredPage) -> bool:
        return all(self._token_matches(token, self._page_tokens(page)) for token in self.tokens)

    def _page_tokens(self, page: DiscoveredPage) -> set[str]:
        return (
            self._tokenize(page.title)
            | self._tokenize(page.snippet)
            | self._tokenize(page.url)
        )

    @staticmethod
    def _token_matches(token: str, available: set[str]) -> bool:
        return token in available or f"{token}s" in available

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))
