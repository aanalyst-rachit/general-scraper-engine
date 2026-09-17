# Programmatic API

## Package Structure

```text
scraper/
├── models.py
├── discovery.py
├── acquisition.py
├── fetcher.py
├── browser_fetcher.py
├── parser.py
├── extraction.py
├── structured_data.py
├── registry.py
├── relevance.py
├── location.py
├── content_quality.py
├── quality.py
├── normalizer.py
├── concurrency.py
├── crawler.py
├── cache/
│   ├── discovery.py
│   └── fetch.py
├── providers/
│   ├── brave.py
│   ├── searxng.py
│   ├── firecrawl.py
│   ├── scrape_do.py
│   └── scrapingdog.py
├── source_adapter.py
├── source_google_maps.py
├── source_google_maps_browser.py
├── source_justdial_browser.py
├── database/
│   ├── repository.py
│   ├── duckdb.py
│   └── run_metrics.py
└── engine.py
```

The package currently keeps `scraper/__init__.py` empty. Public programmatic usage therefore imports the required classes and functions from their defining modules rather than relying on package-level aliases.

## Main Entry Point

The high-level `scrape()` function in `scraper.engine` is the main programmatic pipeline entry point.

```python
from scraper.discovery import SearchRequest, WebDiscovery
from scraper.engine import scrape
from scraper.providers.brave import BraveSearchProvider

request = SearchRequest(
    keyword="dentist",
    location="Shahjahanpur",
    requirements="clinic",
    limit=20,
)

provider = BraveSearchProvider()
discovery = WebDiscovery(provider)
result = scrape(request, discovery)
```

`scrape()` accepts optional fetcher, parser, normalizer, relevance, location, repository, and related pipeline components so callers can replace individual stages without changing the high-level engine contract.

## Core Data Types

- `SearchRequest` — describes keyword, location, requirements, category, and result limit.
- `DiscoveredPage` — represents a discovery result before acquisition.
- `FetchedPage` — represents acquired HTML and its response metadata or failure.
- `Lead` — normalized lead data including identity, contact, location, business context, and source information.
- `ScrapeResult` — contains accepted leads together with discovery, acquisition, quality, provider, cache, and failure measurements.
## Discovery API

- `DiscoveryProvider` — provider protocol for web discovery implementations.
- `WebDiscovery` — coordinates discovery and optional discovery caching.
- `BraveSearchProvider` — Brave Search API implementation.
- `SearXNGProvider` — SearXNG discovery implementation.
- `DiscoveryCache` — optional provider-result cache with configurable freshness policies.

Discovery cache policies currently include `general` (24 hours), `high_change` (1 hour), and `stable_directory` (7 days).

## Acquisition API

- `AcquisitionStrategy` — provider-neutral acquisition contract.
- `FetchRequest` — native acquisition request.
- `ExternalFetchRequest` — external-provider acquisition request.
- `HTTPFetcherAdapter` — adapts `PageFetcher` to the acquisition contract.
- `AutoFetcher` — attempts HTTP acquisition first and can fall back to browser acquisition after content-quality classification.
- `BrowserFetcher` — optional Playwright-based browser acquisition.
- `ExternalFetcher` — contract implemented by external acquisition providers.
- `PolicyAwareExternalFetcher` — applies policy checks before external acquisition.
- `CachedFetcher` — wraps acquisition with fetch-result caching.

Current external acquisition providers are `FirecrawlProvider`, `ScrapeDoProvider`, and `ScrapingdogProvider`.

## Parsing and Extraction API

- `PageParser` — generic HTML and structured-data lead parser.
- `StructuredDataExtractor` — extracts supported JSON-LD / Schema.org information.
- `ExtractionStrategy` — contract for extraction implementations.
- `ParserRegistry` — resolves source-specific parsers before generic fallback.
- `ExtractionRegistry` — manages extraction strategies.
## Relevance and Quality API

- `KeywordRelevance` — keyword matching.
- `LocationRelevance` — requested-location matching.
- `CategoryRelevance` — category matching.
- `RequirementsRelevance` — requirements matching.
- `LocationValidator` — validates extracted location evidence.
- `LeadQuality` — validates deterministic lead-quality dimensions.
- `ContentQualityClassifier` — classifies fetched content before browser fallback or downstream parsing.

Content-quality categories include `valid_content`, `empty_content`, `thin_content`, `js_shell`, `error_page`, `block_page`, `access_blocked`, `rate_limited`, and `auth_required`.

## Normalization and Deduplication

`LeadNormalizer` standardizes extracted values, derives identity keys, deduplicates records, and merges complementary information from duplicate leads.

## Concurrency and Crawling

- `ConcurrencyConfig` — configures global and per-domain concurrency limits.
- `BoundedExecutor` — executes bounded concurrent work.
- `DomainConcurrencyLimiter` — limits concurrent work for individual domains.
- `SiteCrawler` — performs bounded same-site or allowed-domain crawling.
- `BoundedExecutor.map_isolated()` — preserves input order while isolating individual batch failures.

`SiteCrawler` defaults to `max_pages=10` and `max_depth=1`.
## Caching

`FetchCache` provides persistent fetch-result caching. The default fetch-cache policies are `general` (24 hours), `high_change` (1 hour), and `stable` (7 days).

`CachedFetcher` caches successful fetched pages and records cache hit/miss measurements.

## Persistence and Run Metrics

- `LeadRepository` — repository contract for lead persistence.
- `DuckDBLeadRepository` — DuckDB-backed lead repository.
- `RunMetrics` — structured measurements for a scraper run.
- `RunMetricsRepository` — optional persistence for run metrics.

Persistence is optional. A caller can run the scraper entirely in memory and consume the returned `ScrapeResult` directly.

## CLI Compatibility

The same engine is available through the `general-scraper` console command and the existing `run_scraper.py` entry point. The CLI is a convenience layer over the programmatic pipeline rather than a separate scraping implementation.

## Public API Stability

The project intentionally documents explicit module-level imports as the public programmatic interface. No uppercase or package-level compatibility aliases are required by the current API contract.

When replacing a component, prefer the existing protocol or adapter boundary (`DiscoveryProvider`, `AcquisitionStrategy`, `ExternalFetcher`, `ExtractionStrategy`, repository interfaces, and related contracts) instead of coupling new code directly to the engine internals.
