from datetime import datetime, timedelta, timezone

from scraper.discovery import DiscoveredPage
from scraper.cache.discovery import (
    DEFAULT_DISCOVERY_CACHE_TTL,
    DISCOVERY_CACHE_TTLS,
    DiscoveryCache,
    canonical_discovery_cache_key,
)


def make_page(url="https://example.test/company"):
    return DiscoveredPage(
        url=url,
        title="Example Company",
        snippet="Example result",
        source_name="test",
        metadata={"provider_rank": "1"},
    )


def test_canonical_key_is_deterministic():
    first = canonical_discovery_cache_key(
        provider="brave",
        provider_config={"country": "IN", "search_lang": "en"},
        query="software company lucknow",
        search_parameters={"limit": 20},
    )
    second = canonical_discovery_cache_key(
        provider="brave",
        provider_config={"search_lang": "en", "country": "IN"},
        query="software company lucknow",
        search_parameters={"limit": 20},
    )

    assert first == second
    assert len(first) == 64


def test_canonical_key_changes_when_provider_changes():
    first = canonical_discovery_cache_key(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    )
    second = canonical_discovery_cache_key(
        provider="searxng",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    )

    assert first != second


def test_canonical_key_changes_when_search_parameters_change():
    first = canonical_discovery_cache_key(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    )
    second = canonical_discovery_cache_key(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 50},
    )

    assert first != second


def test_cache_starts_empty(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")

    assert cache.get(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    ) is None


def test_cache_round_trip(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=1)

    cache.set(
        provider="brave",
        provider_config={"country": "IN", "search_lang": "en"},
        query="software company",
        search_parameters={"limit": 20},
        results=[make_page()],
        created_at=created_at,
        expires_at=expires_at,
    )

    result = cache.get(
        provider="brave",
        provider_config={"country": "IN", "search_lang": "en"},
        query="software company",
        search_parameters={"limit": 20},
    )

    assert result is not None
    assert result.results == [make_page()]
    assert result.created_at == created_at.replace(tzinfo=None)
    assert result.expires_at == expires_at.replace(tzinfo=None)


def test_expired_entry_is_a_miss(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")
    created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

    cache.set(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
        results=[make_page()],
        created_at=created_at,
        expires_at=expires_at,
    )

    assert cache.get(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    ) is None


def test_different_provider_config_is_a_miss(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")

    cache.set(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
        results=[make_page()],
    )

    assert cache.get(
        provider="brave",
        provider_config={"country": "US"},
        query="software company",
        search_parameters={"limit": 20},
    ) is None


def test_default_ttl_uses_general_policy(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")
    created_at = datetime.now(timezone.utc)

    cache.set(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
        results=[make_page()],
        created_at=created_at,
    )

    result = cache.get(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    )

    assert result is not None
    assert result.expires_at == (
        created_at + DEFAULT_DISCOVERY_CACHE_TTL
    ).replace(tzinfo=None)


def test_ttl_policies_are_explicit():
    assert DISCOVERY_CACHE_TTLS["general"] == timedelta(hours=24)
    assert DISCOVERY_CACHE_TTLS["high_change"] == timedelta(hours=1)
    assert DISCOVERY_CACHE_TTLS["stable_directory"] == timedelta(days=7)


def test_named_ttl_policy_is_applied(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")
    created_at = datetime.now(timezone.utc)

    cache.set(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
        results=[make_page()],
        created_at=created_at,
        ttl_policy="high_change",
    )

    result = cache.get(
        provider="brave",
        provider_config={"country": "IN"},
        query="software company",
        search_parameters={"limit": 20},
    )

    assert result is not None
    assert result.expires_at == (
        created_at + timedelta(hours=1)
    ).replace(tzinfo=None)


def test_unknown_ttl_policy_is_rejected(tmp_path):
    cache = DiscoveryCache(tmp_path / "discovery.duckdb")

    try:
        cache.set(
            provider="brave",
            provider_config={"country": "IN"},
            query="software company",
            search_parameters={"limit": 20},
            results=[make_page()],
            ttl_policy="unknown",
        )
    except ValueError as exc:
        assert "unknown discovery cache TTL policy" in str(exc)
    else:
        raise AssertionError("unknown TTL policy should be rejected")


def test_cache_identity_excludes_secret_provider_credentials():
    from scraper.discovery import WebDiscovery
    from scraper.providers.brave import BraveSearchProvider

    provider = object.__new__(BraveSearchProvider)
    provider.country = "IN"
    provider.search_lang = "en"
    provider.api_key = "secret-value"

    discovery = WebDiscovery(providers=[provider])
    identity = discovery._cache_provider_identity(provider)

    assert identity == "brave"
    config = discovery._cache_provider_config(provider)
    assert config == {"country": "IN", "search_lang": "en"}
    assert "api_key" not in config


def test_cache_identity_supports_searxng_configuration():
    from scraper.discovery import WebDiscovery
    from scraper.providers.searxng import SearXNGProvider

    provider = object.__new__(SearXNGProvider)
    provider.base_url = "http://127.0.0.1:8080"

    discovery = WebDiscovery(providers=[provider])

    assert discovery._cache_provider_identity(provider) == "searxng"
    assert discovery._cache_provider_config(provider) == {
        "base_url": "http://127.0.0.1:8080"
    }


def test_discovery_cache_is_opt_in():
    from scraper.discovery import WebDiscovery

    discovery = WebDiscovery()

    assert discovery.cache is None
