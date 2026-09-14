from dataclasses import dataclass, field
from typing import Protocol


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


class WebDiscovery:
    def __init__(self, providers: list[DiscoveryProvider] | None = None):
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

        for provider in self.providers:
            remaining = request.limit - len(results)
            if remaining <= 0:
                break

            for query in queries:
                remaining = request.limit - len(results)
                if remaining <= 0:
                    break

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
