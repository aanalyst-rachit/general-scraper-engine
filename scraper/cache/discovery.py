from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any


DISCOVERY_CACHE_TTLS = {
    "general": timedelta(hours=24),
    "high_change": timedelta(hours=1),
    "stable_directory": timedelta(days=7),
}
DEFAULT_DISCOVERY_CACHE_TTL = DISCOVERY_CACHE_TTLS["general"]

import duckdb

if TYPE_CHECKING:
    from scraper.discovery import DiscoveredPage


@dataclass(frozen=True)
class DiscoveryCacheEntry:
    results: list[DiscoveredPage]
    created_at: datetime
    expires_at: datetime


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_discovery_cache_key(
    *,
    provider: str,
    provider_config: dict[str, Any],
    query: str,
    search_parameters: dict[str, Any],
) -> str:
    payload = {
        "provider": provider.strip(),
        "provider_config": provider_config,
        "query": query.strip(),
        "search_parameters": search_parameters,
    }
    return hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


class DiscoveryCache:
    def __init__(
        self,
        database_path: str | Path = "data/discovery_cache.duckdb",
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = duckdb.connect(str(self.database_path))
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS discovery_cache (
                    cache_key VARCHAR PRIMARY KEY,
                    provider VARCHAR NOT NULL,
                    provider_config JSON NOT NULL,
                    query VARCHAR NOT NULL,
                    search_parameters JSON NOT NULL,
                    results JSON NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
                """
            )

    def get(
        self,
        *,
        provider: str,
        provider_config: dict[str, Any],
        query: str,
        search_parameters: dict[str, Any],
    ) -> DiscoveryCacheEntry | None:
        cache_key = canonical_discovery_cache_key(
            provider=provider,
            provider_config=provider_config,
            query=query,
            search_parameters=search_parameters,
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        row = self._connection.execute(
                """
                SELECT results, created_at, expires_at
                FROM discovery_cache
                WHERE cache_key = ?
                """,
                [cache_key],
            ).fetchone()

        if row is None:
            return None

        results_json, created_at, expires_at = row

        if expires_at <= now:
            return None

        from scraper.discovery import DiscoveredPage

        raw_results = json.loads(results_json)
        results = [
            DiscoveredPage(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                snippet=str(item.get("snippet", "")),
                source_name=str(item.get("source_name", "")),
                metadata=dict(item.get("metadata", {})),
            )
            for item in raw_results
        ]

        return DiscoveryCacheEntry(
            results=results,
            created_at=created_at,
            expires_at=expires_at,
        )

    def set(
        self,
        *,
        provider: str,
        provider_config: dict[str, Any],
        query: str,
        search_parameters: dict[str, Any],
        results: list[DiscoveredPage],
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
        ttl: timedelta | None = None,
        ttl_policy: str = "general",
    ) -> None:
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        if expires_at is None:
            if ttl is None:
                try:
                    ttl = DISCOVERY_CACHE_TTLS[ttl_policy]
                except KeyError as exc:
                    raise ValueError(
                        f"unknown discovery cache TTL policy: {ttl_policy}"
                    ) from exc
            expires_at = created_at + ttl

        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
        expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at")

        cache_key = canonical_discovery_cache_key(
            provider=provider,
            provider_config=provider_config,
            query=query,
            search_parameters=search_parameters,
        )

        serialized_results = [
            {
                "url": page.url,
                "title": page.title,
                "snippet": page.snippet,
                "source_name": page.source_name,
                "metadata": page.metadata,
            }
            for page in results
        ]

        self._connection.execute(
                """
                INSERT INTO discovery_cache (
                    cache_key,
                    provider,
                    provider_config,
                    query,
                    search_parameters,
                    results,
                    created_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (cache_key) DO UPDATE SET
                    provider = excluded.provider,
                    provider_config = excluded.provider_config,
                    query = excluded.query,
                    search_parameters = excluded.search_parameters,
                    results = excluded.results,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                [
                    cache_key,
                    provider.strip(),
                    json.dumps(provider_config, sort_keys=True),
                    query.strip(),
                    json.dumps(search_parameters, sort_keys=True),
                    json.dumps(serialized_results, ensure_ascii=False),
                    created_at,
                    expires_at,
                ],
            )
    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "DiscoveryCache":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
