from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scraper.fetcher import FetchedPage
from urllib.parse import urlsplit, urlunsplit

import duckdb


FETCH_CACHE_TTLS = {
    "general": timedelta(hours=24),
    "high_change": timedelta(hours=1),
    "stable": timedelta(days=7),
}

DEFAULT_FETCH_CACHE_TTL = FETCH_CACHE_TTLS["general"]


@dataclass(frozen=True)
class FetchCacheEntry:
    url: str
    final_url: str
    acquisition_strategy: str
    status_code: int
    content_type: str
    content_hash: str
    html: str
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any]

    def to_fetched_page(self) -> FetchedPage:
        return FetchedPage(
            url=self.url,
            final_url=self.final_url,
            status_code=self.status_code,
            content_type=self.content_type,
            html=self.html,
            error="",
        )


def canonical_fetch_url(url: str) -> str:
    value = url.strip()
    parsed = urlsplit(value)

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if parsed.port is not None:
        default_port = (
            (scheme == "http" and parsed.port == 80)
            or (scheme == "https" and parsed.port == 443)
        )
        netloc = hostname if default_port else f"{hostname}:{parsed.port}"
    else:
        netloc = hostname

    path = parsed.path or "/"

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            parsed.query,
            "",
        )
    )


def canonical_fetch_cache_key(
    *,
    url: str,
    acquisition_strategy: str,
) -> str:
    payload = {
        "url": canonical_fetch_url(url),
        "acquisition_strategy": acquisition_strategy.strip().lower(),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


class FetchCache:
    def __init__(
        self,
        database_path: str | Path = "data/fetch_cache.duckdb",
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = duckdb.connect(str(self.database_path))
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fetch_cache (
                cache_key VARCHAR PRIMARY KEY,
                canonical_url VARCHAR NOT NULL,
                acquisition_strategy VARCHAR NOT NULL,
                status_code INTEGER NOT NULL,
                content_type VARCHAR NOT NULL,
                content_hash VARCHAR NOT NULL,
                content_gzip BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                metadata JSON NOT NULL
            )
            """
        )

    def get(
        self,
        *,
        url: str,
        acquisition_strategy: str,
    ) -> FetchCacheEntry | None:
        cache_key = canonical_fetch_cache_key(
            url=url,
            acquisition_strategy=acquisition_strategy,
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        row = self._connection.execute(
            """
            SELECT
                canonical_url,
                acquisition_strategy,
                status_code,
                content_type,
                content_hash,
                content_gzip,
                created_at,
                expires_at,
                metadata
            FROM fetch_cache
            WHERE cache_key = ?
            """,
            [cache_key],
        ).fetchone()

        if row is None:
            return None

        (
            canonical_url,
            stored_strategy,
            status_code,
            content_type,
            content_hash,
            content_gzip,
            created_at,
            expires_at,
            metadata_json,
        ) = row

        if expires_at <= now:
            return None

        html = gzip.decompress(bytes(content_gzip)).decode("utf-8")

        return FetchCacheEntry(
            url=canonical_url,
            final_url=str(
                json.loads(metadata_json).get("final_url", canonical_url)
            ),
            acquisition_strategy=stored_strategy,
            status_code=status_code,
            content_type=content_type,
            content_hash=content_hash,
            html=html,
            created_at=created_at,
            expires_at=expires_at,
            metadata=dict(json.loads(metadata_json)),
        )

    def set(
        self,
        *,
        url: str,
        acquisition_strategy: str,
        status_code: int,
        content_type: str,
        html: str,
        final_url: str = "",
        metadata: dict[str, Any] | None = None,
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
                    ttl = FETCH_CACHE_TTLS[ttl_policy]
                except KeyError as exc:
                    raise ValueError(
                        f"unknown fetch cache TTL policy: {ttl_policy}"
                    ) from exc
            expires_at = created_at + ttl

        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
        expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at")

        canonical_url = canonical_fetch_url(url)
        strategy = acquisition_strategy.strip().lower()
        html_bytes = html.encode("utf-8")
        content_hash = hashlib.sha256(html_bytes).hexdigest()
        content_gzip = gzip.compress(html_bytes, compresslevel=6)

        cache_key = canonical_fetch_cache_key(
            url=url,
            acquisition_strategy=strategy,
        )

        stored_metadata = dict(metadata or {})
        stored_metadata["final_url"] = final_url or canonical_url
        stored_metadata["cached_content_encoding"] = "gzip"

        self._connection.execute(
            """
            INSERT INTO fetch_cache (
                cache_key,
                canonical_url,
                acquisition_strategy,
                status_code,
                content_type,
                content_hash,
                content_gzip,
                created_at,
                expires_at,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (cache_key) DO UPDATE SET
                canonical_url = excluded.canonical_url,
                acquisition_strategy = excluded.acquisition_strategy,
                status_code = excluded.status_code,
                content_type = excluded.content_type,
                content_hash = excluded.content_hash,
                content_gzip = excluded.content_gzip,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                metadata = excluded.metadata
            """,
            [
                cache_key,
                canonical_url,
                strategy,
                status_code,
                content_type,
                content_hash,
                content_gzip,
                created_at,
                expires_at,
                json.dumps(stored_metadata, ensure_ascii=False, sort_keys=True),
            ],
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "FetchCache":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
