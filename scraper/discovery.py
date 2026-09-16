from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

import httpx


@dataclass(frozen=True)
class SearchRequest:
    keyword: str
    location: str = ""
    requirements: str = ""
    category: str = ""
    limit: int = 50


@dataclass(frozen=True)
class DiscoveredPage:
    url: str
    title: str = ""
    snippet: str = ""
    source_name: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


class DiscoveryProvider(Protocol):
    def search(self, query: str, limit: int = 20) -> list[DiscoveredPage]:
        ...


class ProviderFailureCategory(str, Enum):
    NO_RESULTS = "no-results"
    TIMEOUT = "timeout"
    AUTH = "auth"
    RATE_LIMIT = "rate-limit"
    SERVER_ERROR = "server-error"
    INVALID_RESPONSE = "invalid-response"


@dataclass(frozen=True)
class ProviderSearchResult:
    pages: list[DiscoveredPage]
    failure: ProviderFailureCategory | None = None


class DiscoveryQualityPolicy:
    """Optional deterministic policy for deciding whether results are useful."""

    def __init__(
        self,
        *,
        keyword: str = "",
        location: str = "",
        category: str = "",
        requirements: str = "",
        minimum_results: int = 1,
    ) -> None:
        if minimum_results < 0:
            raise ValueError("minimum_results must not be negative")

        self.minimum_results = minimum_results

        from scraper.relevance import (
            CategoryRelevance,
            KeywordRelevance,
            LocationRelevance,
            RequirementsRelevance,
        )

        self.keyword = KeywordRelevance(keyword) if keyword.strip() else None
        self.location = LocationRelevance(location) if location.strip() else None
        self.category = CategoryRelevance(category) if category.strip() else None
        self.requirements = (
            RequirementsRelevance(requirements)
            if requirements.strip()
            else None
        )

    def acceptable(self, pages: list[DiscoveredPage]) -> bool:
        if len(pages) < self.minimum_results:
            return False

        if not pages:
            return self.minimum_results == 0

        checks = [
            self.keyword,
            self.location,
            self.category,
            self.requirements,
        ]

        active_checks = [check for check in checks if check is not None]
        if not active_checks:
            return True

        return any(
            all(check.is_relevant(page) for check in active_checks)
            for page in pages
        )


class ProviderRouter:
    """Routes discovery through a primary provider and explicit fallbacks."""

    def __init__(
        self,
        primary: DiscoveryProvider,
        fallbacks: list[DiscoveryProvider] | None = None,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []

    @property
    def providers(self) -> list[DiscoveryProvider]:
        return [self.primary, *self.fallbacks]

    def search(
        self,
        query: str,
        limit: int = 20,
        quality_policy: DiscoveryQualityPolicy | None = None,
    ) -> ProviderSearchResult:
        if limit <= 0:
            return ProviderSearchResult([])

        last_failure: ProviderFailureCategory | None = None

        for provider in self.providers:
            try:
                pages = provider.search(query, limit=limit)
            except (TimeoutError, httpx.TimeoutException):
                last_failure = ProviderFailureCategory.TIMEOUT
                continue
            except PermissionError:
                last_failure = ProviderFailureCategory.AUTH
                continue
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                if status_code in (401, 403):
                    last_failure = ProviderFailureCategory.AUTH
                elif status_code == 429:
                    last_failure = ProviderFailureCategory.RATE_LIMIT
                elif 500 <= status_code <= 599:
                    last_failure = ProviderFailureCategory.SERVER_ERROR
                else:
                    last_failure = ProviderFailureCategory.INVALID_RESPONSE
                continue
            except httpx.RequestError:
                last_failure = ProviderFailureCategory.SERVER_ERROR
                continue
            except ValueError:
                last_failure = ProviderFailureCategory.INVALID_RESPONSE
                continue
            except Exception:
                last_failure = ProviderFailureCategory.INVALID_RESPONSE
                continue

            if not pages:
                last_failure = ProviderFailureCategory.NO_RESULTS
                continue

            if quality_policy is None or quality_policy.acceptable(pages):
                return ProviderSearchResult(pages)

            # Quality rejection is intentionally separate from provider failure.
            # The next explicit fallback gets an opportunity to provide better results.
            continue

        return ProviderSearchResult([], failure=last_failure)


class WebDiscovery:
    def __init__(
        self,
        providers: list[DiscoveryProvider] | None = None,
        *,
        primary_provider: DiscoveryProvider | None = None,
        fallback_providers: list[DiscoveryProvider] | None = None,
        quality_policy: DiscoveryQualityPolicy | None = None,
    ):
        self.quality_policy = quality_policy

        if primary_provider is not None:
            self.router = ProviderRouter(
                primary_provider,
                fallback_providers,
            )
            self.providers = self.router.providers
        else:
            self.router = None
            self.providers = providers or []

    def build_queries(self, request: SearchRequest) -> list[str]:
        keyword = request.keyword.strip()
        location = request.location.strip()
        requirements = request.requirements.strip()

        if not keyword:
            raise ValueError("keyword must not be empty")

        base = f"{keyword} {location}".strip()
        queries = [base]

        if location:
            queries.extend([
                f"{keyword} in {location}",
                f"{keyword} near {location}",
                f"{keyword} {location} contact",
                f"{keyword} {location} phone",
                f"{keyword} {location} address",
            ])

        if requirements:
            queries.append(f"{base} {requirements}".strip())

        return list(dict.fromkeys(query.strip() for query in queries if query.strip()))

    def discover(self, request: SearchRequest) -> list[DiscoveredPage]:
        if request.limit <= 0:
            return []

        results: list[DiscoveredPage] = []
        seen_urls: set[str] = set()

        queries = self.build_queries(request)

        if self.router is not None:
            providers_and_queries = [
                (self.router, query)
                for query in queries
            ]
        else:
            providers_and_queries = [
                (provider, query)
                for provider in self.providers
                for query in queries
            ]

        for provider, query in providers_and_queries:
            remaining = request.limit - len(results)
            if remaining <= 0:
                break

            if self.router is not None:
                search_result = provider.search(
                    query,
                    limit=remaining,
                    quality_policy=self.quality_policy,
                )
                pages = search_result.pages
            else:
                pages = provider.search(query, limit=remaining)

            for page in pages:
                url = page.url.strip()
                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)
                results.append(page)

                if len(results) >= request.limit:
                    break

        return results
