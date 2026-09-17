# General Scraper Engine

A modular, policy-aware web acquisition and lead extraction engine with HTTP-first fetching, browser fallback, optional external acquisition providers, crawling, caching, structured extraction, relevance filtering, quality validation, normalization, deduplication, and DuckDB persistence.

## Overview

The engine upgrades a traditional synchronous HTTP lead scraper into a pluggable web acquisition pipeline:

```text
Discovery
    ↓
Relevance
    ↓
Policy
    ↓
Acquisition
    ↓
Content Quality
    ↓
Parse / Extract
    ↓
Location / Lead Quality
    ↓
Normalize / Deduplicate
    ↓
Persistence / Output
```

HTTP remains the cheapest default acquisition method. Browser and external-provider strategies are introduced only when content or workload requires them.

## Features

### Discovery

- Brave Search Web API
- SearXNG JSON search
- Pluggable discovery-provider protocol
- Discovery-result caching
- URL deduplication
- Search by keyword, location, and requirements

### HTTP Acquisition

- HTTP/HTTPS fetching
- Redirect handling
- Timeouts
- HTTP error handling
- Retryable server failures
- Non-HTML response rejection
- Robots.txt policy checks
- Crawl-delay support
- Request throttling
- Per-domain request limits
- Structured fetch-failure categories

### Browser Acquisition

Optional Playwright-based browser acquisition for pages where native HTTP fetching produces insufficient content.

Browser fallback can be triggered by content-quality classifications such as:

- `empty_content`
- `thin_content`
- `js_shell`

Browser acquisition supports:

- Headless Chromium
- Configurable wait time
- Selector waiting
- Click actions
- Scrolling
- Bounded browser concurrency

### External Acquisition Providers

Optional external acquisition adapters:

- Firecrawl
- Scrape.do
- Scrapingdog

External providers are routed through policy-aware acquisition boundaries and are not required for normal HTTP-first operation.

### Extraction

Deterministic extraction from:

- JSON-LD
- Schema.org
- Meta descriptions
- OpenGraph metadata
- Title information
- Contact information
- Phone numbers
- Email addresses
- Addresses
- Visible page content

Parser and extraction registries allow additional strategies without rewriting the core engine.

### Relevance

Candidates can be evaluated using:

- Keyword relevance
- Location relevance
- Category relevance
- Requirements relevance

### Location and Quality

- Location validation
- Lead-quality evaluation
- Content-quality classification
- Failed-page isolation
- Structured quality metrics

Content-quality classifications:

| Classification   | Description                          |
|------------------|--------------------------------------|
| `valid_content`  | Usable page content                  |
| `empty_content`  | No meaningful content                |
| `thin_content`   | Insufficient content                 |
| `js_shell`       | JavaScript-rendered shell            |
| `error_page`     | Error page                           |
| `block_page`     | Blocked page                         |
| `access_blocked` | Access blocked                       |
| `rate_limited`   | Rate limited                         |
| `auth_required`  | Authentication required              |

### Crawling

Bounded same-site crawling with configurable:

- Maximum pages
- Maximum depth
- Allowed domains
- Include / exclude patterns
- Concurrency

Default limits are intentionally conservative.

### Caching

Two cache layers:

- Discovery cache
- Fetch-result cache

Fetch caching uses DuckDB and supports different TTL policies for general, high-change, and stable content.

### Concurrency

Bounded concurrency utilities for:

- Global concurrency
- Per-domain concurrency
- Batch processing
- Isolated task failures

Concurrency is intentionally bounded to prevent uncontrolled request bursts.

### Persistence

Results can be written to:

- Terminal output
- JSON
- CSV
- DuckDB

Run-level metrics can also be stored in DuckDB.

## Architecture

```text
Search / URL / Crawl Request
        ↓
Discovery / Source Router
        ↓
Discovery Cache
        ↓
DiscoveredPage[]
        ↓
Relevance / Policy Filter
        ↓
Acquisition Router
        ↓
HTTP → Content Quality → Browser → External Provider
        ↓
Content / Extraction Router
        ↓
Structured Data / Site Parser / Generic Parser
        ↓
Location / Lead Quality Validation
        ↓
Normalize + Deduplicate
        ↓
DuckDB / JSON / CSV / Terminal Output
        +
Run Metrics
```

### Discovery

`WebDiscovery` delegates search requests to implementations of the `DiscoveryProvider` protocol.

Current providers:

- `BraveSearchProvider`
- `SearXNGProvider`

Discovery results can be cached through `DiscoveryCache`.

### Acquisition

The acquisition layer separates fetching from discovery and parsing.

Normal path (HTTP-first):

```text
HTTPFetcherAdapter
        ↓
PageFetcher
        ↓
Content Quality
        ↓
Browser fallback when required
```

`AutoFetcher` evaluates fetched content and can route browser-relevant pages to `BrowserFetcher`.

External acquisition providers can be used when an external scraping service is explicitly selected.

### Policy

Native HTTP acquisition respects:

- Robots.txt
- Crawl delay
- Request limits
- URL validation
- Retry policy
- Public HTTP/HTTPS boundaries

External acquisition is also passed through policy-aware boundaries.

The engine does **not** silently bypass:

- Robots restrictions
- Authentication
- CAPTCHA
- Access controls

### Parsing and Extraction

```text
Fetched Content
      ↓
Content Quality
      ↓
Parser / Extraction Registry
      ↓
Structured Data
      +
Generic HTML Extraction
      +
Source-specific Adapter
      ↓
Lead
```

JSON-LD and Schema.org are preferred when reliable structured information is available.

### Relevance and Location

Discovered and acquired pages are evaluated before becoming final leads.

Relevance filters can evaluate keyword, location, category, and requirements.

Location validation provides an additional check before persistence.

### Normalization and Deduplication

`LeadNormalizer` standardizes:

- Text
- Names
- Phone numbers
- Email addresses
- URLs

Identity keys can use available combinations of:

- Phone
- Email
- Website / name
- Company / name
- Address
- Profession
- Location

Duplicate leads can be merged while preserving source URLs and available information.

### Metrics

Run-level metrics can track:

- Acquisition strategy
- Browser usage
- External-provider usage
- Cache hits / misses
- Content-quality results
- Lead-quality results
- Failure categories
- Workload results

## Installation

Python 3.12 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
```

This installs the `general-scraper` command.

The original script entry point remains supported:

```bash
python run_scraper.py
```

## Requirements

Core requirements:

- Python 3.12+
- Internet access for live web acquisition
- A discovery provider

**Brave Search**

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

**SearXNG** — provide the URL of a running SearXNG instance.

## Quick Start

### Brave Search

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"

general-scraper \
  --provider brave \
  --keyword "dentist" \
  --location "Shahjahanpur" \
  --requirements "clinic"
```

### SearXNG

```bash
general-scraper \
  --provider searxng \
  --searxng-url "http://127.0.0.1:8080" \
  --keyword "dentist" \
  --location "Shahjahanpur" \
  --requirements "clinic"
```

Original script entry point:

```bash
python run_scraper.py \
  --provider brave \
  --keyword "dentist" \
  --location "Shahjahanpur"
```

## Programmatic API

Main modules:

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

### Example

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

for lead in result.leads:
    print(lead.to_dict())
```

### Core Types

- `SearchRequest`
- `DiscoveredPage`
- `FetchedPage`
- `Lead`
- `ScrapeResult`
- `DiscoveryProvider`
- `WebDiscovery`
- `AcquisitionStrategy`
- `FetchRequest`
- `ExternalFetchRequest`
- `HTTPFetcherAdapter`
- `AutoFetcher`
- `BrowserFetcher`
- `ExternalFetcher`
- `PolicyAwareExternalFetcher`
- `CachedFetcher`
- `PageParser`
- `ParserRegistry`
- `ExtractionRegistry`
- `ContentQualityClassifier`
- `LocationValidator`
- `LeadQuality`
- `LeadRepository`
- `DuckDBLeadRepository`
- `RunMetrics`
- `SiteCrawler`

The high-level `scrape()` function in `scraper.engine` is the main programmatic entry point. It accepts composable discovery, acquisition, parsing, relevance, location, and persistence components.

## Discovery Providers

### Brave Search

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

Supports explicit API-key injection when used programmatically.

### SearXNG

```python
from scraper.providers.searxng import SearXNGProvider

provider = SearXNGProvider(base_url="http://127.0.0.1:8080")
```

Default endpoint: `http://127.0.0.1:8080`

## Acquisition Providers

### Native HTTP

Default and lowest-cost path:

```python
from scraper.acquisition import HTTPFetcherAdapter
```

### Browser

Requires Playwright:

```bash
pip install playwright
playwright install chromium
```

Use only when native HTTP content is insufficient.

### External Providers

| Provider    | Environment Variable          |
|-------------|-------------------------------|
| Firecrawl   | `FIRECRAWL_API_KEY`           |
| Scrape.do   | `SCRAPE_DO_API_KEY`           |
| Scrapingdog | `SCRAPINGDOG_API_KEY`         |

External adapters are programmatic integrations. The CLI discovery interface exposes Brave and SearXNG.

## Policy and Public-Web Boundaries

Designed for public-web acquisition.

Native HTTP fetching can enforce:

- Robots.txt
- Crawl delay
- Per-domain request limits
- Retry policy
- URL validation
- Request throttling

A robots-policy failure is treated as a policy failure (not silently ignored).

The engine does **not** provide mechanisms to bypass:

- Authentication
- CAPTCHA challenges
- Access controls
- Robots restrictions

## Failure Categories

**Fetch failures:**

```text
timeout
policy
request-limit
auth
access-blocked
rate-limit
server-error
invalid-response
```

**Content quality:**

```text
valid_content
empty_content
thin_content
js_shell
error_page
block_page
access_blocked
rate_limited
auth_required
```

Only browser-relevant cases (`empty_content`, `thin_content`, `js_shell`) are candidates for automatic browser fallback.

Individual acquisition failures are isolated — one failed page does not terminate the scrape.

## Crawling

`SiteCrawler` provides bounded same-site crawling.

**Default limits:**

```text
max_pages = 10
max_depth = 1
global crawler concurrency = 1
```

Supports:

- Same-domain restrictions
- Explicit allowed domains
- Include / exclude patterns
- Bounded page count and depth
- Isolated acquisition failures

## Caching

### Discovery Cache

`DiscoveryCache` stores discovered URLs to reduce repeated search-provider calls.

### Fetch Cache

`FetchCache` + `CachedFetcher` cache successful fetch results.

Default location: `data/fetch_cache.duckdb`

**Default TTL policies:**

| Content Type       | TTL      |
|--------------------|----------|
| General content    | 24 hours |
| High-change content| 1 hour   |
| Stable content     | 7 days   |

Only successful pages are cached.

## Concurrency

Bounded concurrency via:

- `ConcurrencyConfig`
- `BoundedExecutor`
- `DomainConcurrencyLimiter`

`BoundedExecutor.map_isolated()` isolates individual workload failures without cancelling unrelated work.

## Database

DuckDB is supported for local persistence.

```bash
general-scraper \
  --provider brave \
  --keyword "dentist" \
  --location "Shahjahanpur" \
  --db-path data/my-leads.duckdb
```

The repository normalizes leads and uses identity keys to avoid duplicate records. Run metrics can also be persisted.

## Content Quality

```text
HTTP response
      ↓
ContentQualityClassifier
      ↓
valid_content?
      ├── yes → parsing
      └── no  → browser fallback (when eligible)
```

Browser fallback is not intended to replace HTTP acquisition globally.

## Source Adapters

Source-specific adapters are available through `SourceAdapter` and `SourceAdapterRegistry`.

Current implementations:

- Google Maps HTTP adapter
- Google Maps browser adapter
- Justdial browser adapter

The CLI also exposes direct-source execution for specialized adapters:

- `google-maps` — Google Maps Places API
- `google-maps-browser` — Google Maps browser acquisition
- `justdial-browser` — Justdial browser acquisition

Example:

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

Direct-source results use the common `Lead` model and can be written to JSON, CSV, or DuckDB using the existing output and persistence options.

The `--category` option can filter direct-source results by the normalized Lead category.

Additional specialized adapters should demonstrate measurable value before inclusion.

## Testing

```bash
# Full test suite
pytest -q

# Compile check
python -m compileall -q scraper benchmark tests

# Phase 16 benchmark
python benchmark/phase16/runner.py
```

Benchmark matrix covers:

- Static pages
- Content-quality matrix
- Repeated URLs
- Large batches
- Extraction
- Location and quality
- Sequential vs concurrent acquisition
- HTTP vs browser acquisition
- Native vs external acquisition
- Cache vs no-cache behavior

## Benchmarking Principles

- HTTP remains the default acquisition path
- Browser rendering is fallback-driven
- External scraping services remain optional
- Proxy infrastructure should be evidence-driven
- Deterministic extraction is preferred over AI-first extraction
- Existing public APIs should remain compatible
- Performance changes require benchmark evidence
- Site-specific implementations must demonstrate value
- Project policy must never be silently bypassed

## Compatibility

Supported entry points:

```bash
general-scraper
python run_scraper.py
```

Programmatic usage:

```python
from scraper.engine import scrape
# or
from scraper.engine import ScraperEngine
```

The acquisition layer is composable — native HTTP, browser, and external strategies can be used without rewriting discovery or persistence layers.

## Project Status

Core pipeline, documentation, packaging, benchmark validation, and release-audit work are implemented through **Phase 17**.

Current focus:

```text
Phase 17 — Documentation & Public API
```

The project is undergoing final V1 release checks.

## Deferred Work (Outside v1 Scope)

- Background job queue
- Webhook delivery
- Persistent browser sessions
- Advanced browser workflows
- AI-first extraction and agent workflows
- Large-scale distributed crawling
- Extensive Justdial / OLX parsers
- Residential proxy rotation
- In-house CAPTCHA solving
- Firecrawl-scale cloud orchestration

## Design Principles

1. HTTP is the cheapest and default acquisition path.
2. Browser rendering is fallback-driven, not browser-first.
3. External scraping services are optional.
4. Proxy infrastructure is introduced only when evidence justifies it.
5. Deterministic extraction is preferred over AI-first extraction.
6. Existing public APIs remain compatible wherever practical.
7. Performance decisions require benchmark evidence.
8. Site-specific implementations require demonstrated value.
9. Robots and project policy must never be silently bypassed.
10. Local and self-hosted operation remain first-class.

## License

See [LICENSE](LICENSE).
