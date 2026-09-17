# Architecture

General Scraper Engine is organized as a pluggable acquisition pipeline. Discovery, acquisition, parsing, quality validation, normalization, persistence, and run metrics are separate concerns.

## High-Level Flow

```text
CLI / Programmatic API
        |
        v
SearchRequest
        |
        v
WebDiscovery
        |
        +--> BraveSearchProvider
        +--> SearXNGProvider
        |
        v
Discovery Cache
        |
        v
DiscoveredPage
        |
        v
Relevance Filters
        |
        v
Acquisition
        |
        +--> HTTPFetcherAdapter -> PageFetcher
        |
        +--> AutoFetcher -> HTTP -> ContentQuality -> Browser
        |
        +--> External Provider
        |       +--> Firecrawl
        |       +--> Scrape.do
        |       +--> Scrapingdog
        v
FetchedPage
        |
        v
ParserRegistry / PageParser
        |
        +--> Structured data / generic extraction
        +--> Source-specific parser
        |
        v
Lead
        |
        +--> Location validation
        +--> Lead quality
        |
        v
Normalize / Deduplicate / Merge
        |
        +--> Terminal
        +--> JSON / CSV
        +--> Optional DuckDB
        +--> Optional Run Metrics
```

## Discovery

`WebDiscovery` accepts a `SearchRequest` and delegates discovery to configured providers.

Built-in discovery providers are `BraveSearchProvider` and `SearXNGProvider`. The `DiscoveryProvider` protocol allows additional providers without changing the core discovery pipeline.

Discovery results are represented by `DiscoveredPage`.

## Discovery Caching

`DiscoveryCache` can cache provider results. Its cache key includes provider identity, provider configuration, query, and search parameters.

The built-in policies are `general` (24 hours), `high_change` (1 hour), and `stable_directory` (7 days). Expired entries are treated as cache misses.

## Relevance Filtering

Candidates can be filtered before acquisition using keyword, location, category, and requirements relevance.

## Acquisition

`HTTPFetcherAdapter` wraps the native `PageFetcher` implementation.

`AutoFetcher` starts with HTTP acquisition and uses `ContentQualityClassifier` to determine whether empty, thin, or JavaScript-shell content needs browser fallback.

External acquisition uses the provider-neutral `ExternalFetcher` contract. Current adapters are Firecrawl, Scrape.do, and Scrapingdog.

`PolicyAwareExternalFetcher` can apply the existing robots and request-delay checks before invoking an external provider.

## Concurrency

`BoundedExecutor` provides bounded concurrent execution. `ConcurrencyConfig` supports a global limit and an optional per-domain limit.

`DomainConcurrencyLimiter` prevents concurrent work for one domain from exceeding its configured limit. The crawler and engine reuse these concurrency primitives.

`BoundedExecutor.map_isolated()` preserves input order while capturing individual batch failures instead of aborting the complete batch.

## Crawling

`SiteCrawler` provides bounded crawling with defaults of `max_pages=10` and `max_depth=1`.

The crawler tracks queued and visited URLs, canonicalizes URLs, supports allowed domains and include/exclude patterns, and isolates failed page fetches.

## Parsing and Extraction

`ParserRegistry` can resolve source-specific parsers before the configured `PageParser` fallback.

`PageParser` extracts lead information from JSON-LD / Schema.org and HTML metadata and fallbacks including title, OpenGraph, phone, email, address, and website information.

`StructuredDataExtractor` provides structured-data extraction independently of the generic parser path.

## Content Quality

`ContentQualityClassifier` categorizes fetched pages as `valid_content`, `empty_content`, `thin_content`, `js_shell`, `error_page`, `block_page`, `access_blocked`, `rate_limited`, or `auth_required`.

Only empty, thin, and JavaScript-shell content is marked for browser fallback.

## Lead Quality and Location

`LocationValidator` checks extracted location evidence against the requested location.

`LeadQuality` validates deterministic dimensions including identity, contact information, web presence, location, business context, and source URL.

## Normalization and Deduplication

`LeadNormalizer` standardizes extracted values and merges duplicate leads using available identity evidence while preserving useful source information.

## Persistence and Run Metrics

`DuckDBLeadRepository` provides optional lead persistence. `RunMetricsRepository` can persist discovery, acquisition, failure, quality, provider, browser-fallback, and cache measurements.

## Public-Web Boundary

The engine is intended for public-web acquisition. It does not provide login bypass, CAPTCHA bypass, private-page access, authentication bypass, or access-control circumvention.
