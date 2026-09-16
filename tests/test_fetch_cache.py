from datetime import datetime, timedelta, timezone

import pytest

from scraper.cache.fetch import (
    FETCH_CACHE_TTLS,
    FetchCache,
    canonical_fetch_cache_key,
    canonical_fetch_url,
)


def test_canonical_fetch_url_normalizes_scheme_host_port_and_fragment():
    assert canonical_fetch_url(
        " HTTPS://Example.COM:443/path/page?b=2#a "
    ) == "https://example.com/path/page?b=2"

    assert canonical_fetch_url("http://Example.COM:80") == "http://example.com/"


def test_canonical_fetch_url_preserves_non_default_port_and_query():
    assert canonical_fetch_url(
        "https://Example.COM:8443/a?x=1"
    ) == "https://example.com:8443/a?x=1"


def test_fetch_cache_key_is_deterministic():
    first = canonical_fetch_cache_key(
        url="https://example.com/page#section",
        acquisition_strategy="HTTP",
    )
    second = canonical_fetch_cache_key(
        url="https://EXAMPLE.COM/page",
        acquisition_strategy="http",
    )

    assert first == second
    assert len(first) == 64


def test_fetch_cache_key_changes_with_acquisition_strategy():
    http_key = canonical_fetch_cache_key(
        url="https://example.com/page",
        acquisition_strategy="http",
    )
    browser_key = canonical_fetch_cache_key(
        url="https://example.com/page",
        acquisition_strategy="browser",
    )

    assert http_key != browser_key


def test_fetch_cache_round_trip(tmp_path):
    database_path = tmp_path / "fetch.duckdb"

    with FetchCache(database_path) as cache:
        cache.set(
            url="https://example.com/page#fragment",
            acquisition_strategy="HTTP",
            status_code=200,
            content_type="text/html; charset=utf-8",
            html="<html><body>héllo</body></html>",
            final_url="https://example.com/final",
            metadata={"source": "test", "attempt": 1},
        )

        entry = cache.get(
            url="https://EXAMPLE.COM/page",
            acquisition_strategy="http",
        )

    assert entry is not None
    assert entry.url == "https://example.com/page"
    assert entry.final_url == "https://example.com/final"
    assert entry.acquisition_strategy == "http"
    assert entry.status_code == 200
    assert entry.content_type == "text/html; charset=utf-8"
    assert entry.html == "<html><body>héllo</body></html>"
    assert entry.metadata["source"] == "test"
    assert entry.metadata["attempt"] == 1
    assert entry.metadata["cached_content_encoding"] == "gzip"
    assert len(entry.content_hash) == 64


def test_fetch_cache_content_hash_is_sha256(tmp_path):
    html = "<html>hash me</html>"

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html=html,
        )
        entry = cache.get(
            url="https://example.com",
            acquisition_strategy="http",
        )

    import hashlib

    assert entry is not None
    assert entry.content_hash == hashlib.sha256(
        html.encode("utf-8")
    ).hexdigest()


def test_browser_and_http_entries_are_independent(tmp_path):
    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com/app",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>http</html>",
        )
        cache.set(
            url="https://example.com/app",
            acquisition_strategy="browser",
            status_code=200,
            content_type="text/html",
            html="<html>browser</html>",
        )

        http_entry = cache.get(
            url="https://example.com/app",
            acquisition_strategy="http",
        )
        browser_entry = cache.get(
            url="https://example.com/app",
            acquisition_strategy="browser",
        )

    assert http_entry is not None
    assert browser_entry is not None
    assert http_entry.html == "<html>http</html>"
    assert browser_entry.html == "<html>browser</html>"


def test_missing_entry_returns_none(tmp_path):
    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        assert cache.get(
            url="https://example.com/missing",
            acquisition_strategy="http",
        ) is None


def test_expired_entry_is_cache_miss(tmp_path):
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=2)

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com/expired",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>expired</html>",
            created_at=created_at,
            ttl=timedelta(hours=1),
        )

        assert cache.get(
            url="https://example.com/expired",
            acquisition_strategy="http",
        ) is None


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        ("general", timedelta(hours=24)),
        ("high_change", timedelta(hours=1)),
        ("stable", timedelta(days=7)),
    ],
)
def test_ttl_policies(tmp_path, policy, expected):
    created_at = datetime.now(timezone.utc)

    with FetchCache(tmp_path / f"{policy}.duckdb") as cache:
        cache.set(
            url=f"https://example.com/{policy}",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>ttl</html>",
            created_at=created_at,
            ttl_policy=policy,
        )

        entry = cache.get(
            url=f"https://example.com/{policy}",
            acquisition_strategy="http",
        )

    assert entry is not None
    assert entry.expires_at == (
        created_at + expected
    ).replace(tzinfo=None)


def test_default_ttl_is_general(tmp_path):
    created_at = datetime.now(timezone.utc)

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com/default",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>ttl</html>",
            created_at=created_at,
        )

        entry = cache.get(
            url="https://example.com/default",
            acquisition_strategy="http",
        )

    assert entry is not None
    assert entry.expires_at == (
        created_at + FETCH_CACHE_TTLS["general"]
    ).replace(tzinfo=None)


def test_custom_ttl_overrides_policy(tmp_path):
    created_at = datetime.now(timezone.utc)

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com/custom",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>ttl</html>",
            created_at=created_at,
            ttl=timedelta(minutes=15),
            ttl_policy="stable",
        )

        entry = cache.get(
            url="https://example.com/custom",
            acquisition_strategy="http",
        )

    assert entry is not None
    assert entry.expires_at == (
        created_at + timedelta(minutes=15)
    ).replace(tzinfo=None)


def test_unknown_ttl_policy_raises(tmp_path):
    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        with pytest.raises(ValueError, match="unknown fetch cache TTL policy"):
            cache.set(
                url="https://example.com/ttl",
                acquisition_strategy="http",
                status_code=200,
                content_type="text/html",
                html="<html>ttl</html>",
                ttl_policy="unknown",
            )


def test_invalid_expiry_raises(tmp_path):
    created_at = datetime.now(timezone.utc)

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        with pytest.raises(
            ValueError,
            match="expires_at must be later than created_at",
        ):
            cache.set(
                url="https://example.com/invalid",
                acquisition_strategy="http",
                status_code=200,
                content_type="text/html",
                html="<html>invalid</html>",
                created_at=created_at,
                expires_at=created_at,
            )


def test_set_updates_existing_entry(tmp_path):
    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        cache.set(
            url="https://example.com/update",
            acquisition_strategy="http",
            status_code=200,
            content_type="text/html",
            html="<html>old</html>",
        )
        cache.set(
            url="https://example.com/update",
            acquisition_strategy="http",
            status_code=304,
            content_type="text/html",
            html="<html>new</html>",
        )

        entry = cache.get(
            url="https://example.com/update",
            acquisition_strategy="http",
        )

    assert entry is not None
    assert entry.status_code == 304
    assert entry.html == "<html>new</html>"
