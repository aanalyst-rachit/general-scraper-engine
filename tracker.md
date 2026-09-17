# General Scraper Engine — v1.0.2 Tracker

## v1.0.2 — Architecture & Capability Upgrade

**Status:** SCOPE LOCKED — implementation follows this tracker

### Release Goal

Upgrade General Scraper Engine from a synchronous HTTP-oriented lead scraper into a pluggable web acquisition engine with smart HTTP/browser fallback, bounded concurrency, provider routing, caching, structured extraction, crawling, quality measurement, and optional external scraping-provider integrations.

### Scope Rule

This tracker is the locked v1.0.2 implementation scope. Competitor features from Firecrawl, Scrape.do, and Scrapingdog are treated as R&D inputs, not as requirements to copy wholesale.

---

## PHASE 0 — Baseline & R&D Validation

- [x] Establish reproducible benchmark workload
- [x] Measure discovery latency
- [x] Measure per-page fetch latency
- [x] Measure parse latency
- [x] Measure total run latency
- [x] Measure discovered / filtered / fetched / parsed / valid / duplicate counts
- [x] Categorize HTTP, robots, timeout, block, empty-content, and parse failures
- [x] Measure lead yield and time-to-first-lead
- [x] Compare sequential vs bounded-concurrent execution
- [x] Record baseline before performance architecture changes

## PHASE 1 — Acquisition Architecture

- [x] Preserve existing PageFetcher compatibility
- [x] Introduce acquisition strategy abstraction
- [x] Define FetchRequest / FetchResponse contract
- [x] Define HTTP / browser / external acquisition strategies
- [x] Introduce acquisition router
- [x] Keep robots and policy enforcement above provider-specific infrastructure

## PHASE 2 — Smart HTTP Acquisition

- [x] Audit current PageFetcher for reuse
- [x] Add content-quality detection after HTTP fetch
- [x] Detect thin/empty/JS-shell/error/block pages
- [x] Define deterministic browser-fallback triggers
- [x] Preserve current timeout, retry, robots, and domain-limit behavior
- [x] Evaluate randomized delay separately; do not assume it is already implemented

## PHASE 3 — Browser Fetching

- [x] Evaluate Playwright dependency and runtime footprint
- [x] Implement BrowserFetcher behind acquisition interface
- [x] Support navigation
- [x] Support bounded waiting
- [x] Support selector waiting
- [x] Support controlled scrolling
- [x] Support basic click interaction where required
- [x] Return normalized fetched content through common FetchResponse
- [x] HTTP-first → browser fallback becomes default AUTO strategy
- [x] Keep browser concurrency separately bounded

## PHASE 4 — Async / Bounded Concurrency

- [x] Introduce bounded async execution
- [x] Define global concurrency limit
- [x] Define per-domain concurrency limit
- [ ] Define provider concurrency limit
- [x] Ensure robots/request-delay policy remains enforced
- [x] Benchmark sequential vs concurrent fetch performance
  - Canonical `benchmark/v1_0_2` workload: 26 cases, 25 fetch successes, 1 fetch failure, 25 valid leads, 6751 content bytes.
  - Fresh sequential baseline: 1921.253 ms.
  - Bounded concurrency 4: 2300.985 ms (0.83x vs baseline).
  - Bounded concurrency 8: 1547.554 ms (1.24x vs baseline; 1.49x vs C4).
  - Benchmark runner uses production `scraper.concurrency.BoundedExecutor`; C4/C8 results are independently recorded.
- [x] Avoid unbounded asyncio tasks

## PHASE 5 — Discovery Provider Routing

- [x] Preserve DiscoveryProvider protocol
- [x] Add provider router/policy layer
- [x] Support primary provider and explicit fallback providers
- [x] Categorize provider failures: no-results, timeout, auth, rate-limit, server-error, invalid-response
- [x] Define quality-based fallback policy separately from failure fallback
- [x] Preserve existing query deduplication
- [x] Preserve existing per-run URL deduplication
- [x] Evaluate SearXNG / Brave as current native providers
  - Brave Search Web API and SearXNG JSON providers are implemented, tested, CLI-integrated, and documented.
- [x] Evaluate optional external search providers before implementation
  - No additional external provider was selected for implementation; the provider-agnostic protocol/router remains available for future integrations.

## PHASE 6 — Discovery Cache

- [x] Design discovery cache schema
- [x] Define canonical cache key including provider/config/query/search parameters
- [x] Store creation and expiry timestamps
- [x] Define TTL policy by discovery source/use case
- [x] Implement DuckDB-backed discovery cache only after benchmark validates benefit
  - Benchmark: 20 iterations, 95% cache hit rate, 95% provider-call reduction, 2.72x mean latency speedup.
- [x] Measure cache hit/miss behavior
  - DuckDB benchmark: 19 hits / 1 miss; provider calls reduced from 100 to 5.

## PHASE 7 — Fetch Cache

- [x] Design fetch cache schema
- [x] Include canonical URL, acquisition strategy, status, content type, content hash, timestamps, and metadata
- [x] Define cache invalidation/TTL policy
- [x] Evaluate HTML storage size before committing to DuckDB blob storage
- [x] Implement cache only after storage/performance R&D
- [x] Measure repeated-fetch latency reduction
  - Repeated local HTTP fetch benchmark: 20 iterations, 19 cache hits / 1 miss, 95% hit rate.
  - Baseline mean: 63.537 ms; cached mean: 6.376 ms; 9.965x mean speedup and 89.96% mean latency reduction.
  - Actual underlying fetch calls: 20 baseline vs 1 cached; 95% call reduction.

## PHASE 8 — Content & Extraction Layer

- [x] Introduce content-quality classification
  - Added deterministic classification for valid, empty, thin, JS-shell, HTTP-error, and block/challenge pages; browser fallback remains limited to content-quality cases that can benefit from rendered acquisition.
- [x] Preserve existing generic parser
  - Existing HTML/meta/address/email/phone extraction behavior preserved while JSON-LD extraction was separated into its own strategy.
- [x] Add structured-data extraction path (Schema.org/JSON-LD)
  - Added deterministic Schema.org/JSON-LD extraction with support for entity types, `@graph`, arrays, type lists, malformed-script tolerance, and structured address/category fields.
- [x] Define extraction strategy interface
  - Added `ExtractionStrategy` protocol returning normalized extraction fields or no result.
- [x] Introduce parser/extractor registry
  - Added `ParserRegistry` for domain-specific parsers and `ExtractionRegistry` for ordered extraction strategies.
- [x] Route site-specific parser before generic fallback
  - Engine resolves registered parsers by domain first, uses the generic parser for unknown domains, and falls back to the generic parser when a registered parser returns no lead.
- [x] Keep deterministic extraction ahead of optional AI extraction
  - Deterministic extraction is the only active extraction path; ordered `ExtractionRegistry` provides the extension point for future optional strategies without making AI a prerequisite.
- [x] Evaluate Markdown representation as an optional normalized content format
  - Evaluated against the current architecture. Raw HTML remains the canonical representation because deterministic DOM and JSON-LD extraction depend on HTML structure/metadata; Markdown is not required as an intermediate representation and no conversion dependency is introduced.

## PHASE 9 — Lead Quality & Relevance

- [x] Audit existing LeadQuality and relevance behavior
  - Existing deterministic LeadQuality validation and keyword/location/category/requirements relevance behavior were audited and preserved.
- [x] Define requested-location vs extracted-location validation
  - Added deterministic LocationValidator coverage across locality, city, district, state, location text, and address evidence.
- [x] Detect conflicting location evidence
  - Conflicting free-text location/address evidence is rejected when it contradicts the requested location.
- [x] Define lead quality scoring dimensions
  - LeadQuality now reports deterministic identity, contact, web presence, location, business context, and source evidence dimensions.
- [x] Measure lead quality separately from fetch success
  - Engine results now expose checked, accepted, and rejected quality counts independently of fetched-page counts.
- [x] Preserve current Lead model compatibility
  - Existing Lead fields, defaults, location fields, and to_dict() serialization remain compatible and are covered by regression tests.
- [x] Avoid accepting technically valid but geographically irrelevant leads
  - Geographic relevance is enforced before LeadQuality acceptance, preventing technically valid leads from irrelevant locations from entering final results.


## PHASE 10 — Map & Crawl

- [x] Design bounded site-map operation
  - Added `SiteCrawler` with bounded frontier processing and configurable global/per-domain concurrency.
- [x] Discover internal URLs from a seed URL
  - Crawls links discovered from fetched HTML and keeps the seed-to-page traversal bounded by depth and page limits.
- [x] Canonicalize URLs
  - Normalizes HTTP(S) scheme/host/path, resolves relative URLs, preserves query strings, and removes fragments.
- [x] Deduplicate URLs
  - Canonical URLs are tracked across queued, visited, and discovered candidates so duplicate links are fetched once.
- [x] Support max pages
  - Enforces a strict returned-page budget, including concurrent frontier processing and include-pattern scenarios.
- [x] Support max depth
  - Traversal only expands links while the current page depth is below the configured maximum.
- [x] Support allowed domains
  - Defaults to same-domain crawling and supports an explicit allowed-domain set for bounded cross-domain crawling.
- [x] Support include/exclude URL patterns
  - Applies glob-style include/exclude filters to candidate URLs while retaining seed fetching for discovery.
- [x] Respect robots policy
  - Reuses the existing acquisition layer, including `PageFetcher` robots enforcement; blocked URLs never reach the HTTP client.
- [x] Reuse acquisition and extraction layers
  - Fetches through `AcquisitionStrategy`/`FetchRequest` and returns `FetchedPage` objects that can be processed directly by the existing `PageParser`/extraction pipeline.
- [x] Implement bounded crawler rather than Firecrawl-scale distributed crawling
  - Uses a local bounded executor and domain limiter; no distributed or unbounded crawl scheduling is introduced.

## PHASE 11 — External Scraping Provider Adapters

- [x] Define ExternalFetcher interface
  - Added a provider-neutral `ExternalFetcher` protocol returning the existing `FetchedPage` model.
- [x] Define provider-neutral request/response contract
  - Added immutable `ExternalFetchRequest` with URL, optional rendering, and optional timeout controls; adapters normalize responses to `FetchedPage`.
- [x] Evaluate Firecrawl integration
  - Added an optional Firecrawl adapter using the documented v2 scrape endpoint and HTML response mapping; API credentials are required only when the adapter is instantiated.
- [x] Evaluate Scrape.do integration
  - Added an optional Scrape.do adapter with documented token/URL parameters, optional rendering, timeout mapping, and resolved-URL handling.
- [x] Evaluate Scrapingdog integration
  - Added an optional Scrapingdog adapter with documented API-key/URL parameters and `dynamic=true` rendering support; no undocumented per-request timeout parameter is introduced.
- [x] Keep external providers optional
  - Provider modules are independently importable and are not instantiated by the default acquisition path; credentials are not required for local HTTP/browser operation.
- [x] Do not make any external provider mandatory for local/self-hosted usage
  - `ScraperEngine` continues to use the existing local HTTP/browser acquisition flow by default, with no external service dependency.
- [x] Ensure external providers cannot silently bypass robots/policy decisions
  - Added `PolicyAwareExternalFetcher`, which checks the existing robots policy and request-delay policy before invoking an external provider; blocked or failed policy checks prevent provider invocation.

## PHASE 12 — Specialized Source Adapters

**Goal:** Build specialized public-page parsers/adapters for Google Maps, Justdial, OLX, and LinkedIn, all normalized into the common `Lead` model.

- [x] Define SourceAdapter architecture
  - Common `SearchRequest → SourceAdapter → list[Lead]` contract.
- [x] Build Google Maps browser parser
  - Playwright for public-page rendering.
  - BeautifulSoup for rendered HTML parsing.
  - Real-page fixture and parser regression tests.
  - Detect challenge/block pages and stop safely; never bypass CAPTCHA or bot protections.
- [x] Build Justdial specialized parser
  - Audit public search/listing DOM.
  - Implement Playwright + BeautifulSoup parsing where required.
  - Normalize results into `Lead`.
  - Add fixtures and focused tests.
- [ ] Build OLX specialized parser
  - Audit public listing/search DOM.
  - Implement parser and `Lead` normalization.
  - Add fixtures and focused tests.
- [ ] Build LinkedIn specialized parser
  - Parse publicly accessible pages only.
  - Normalize profile/company data into `Lead`.
  - Login/restricted/challenge pages must stop safely.
  - Add fixtures and focused tests.
- [ ] Common parser validation
  - Handle missing fields safely.
  - Respect requested result limits.
  - Deduplicate source results.
  - Preserve source URLs/source names.
  - Detect challenge/block pages.
  - Add synthetic and real-page fixture regression coverage where practical.
- [ ] Integrate all specialized adapters
  - Register adapters in `SourceAdapterRegistry`.
  - Verify source selection resolves to the correct specialized parser.
  - Run focused and full regression tests.
- [ ] Document specialized source adapters and public-access boundaries
- [ ] Complete Phase 12 tracker + git checkpoint

## PHASE 13 — Anti-Blocking / Operational Resilience

- [x] Build failure taxonomy first
- [x] Detect 403 / 429 / CAPTCHA / bot-block / challenge pages
- [x] Tune retries and throttling from observed evidence
- [x] Evaluate browser fallback before proxy infrastructure
- [x] Evaluate external provider fallback before owning proxy infrastructure
- [x] Residential proxy support remains conditional
- [x] Do not build an in-house CAPTCHA-solving system
- [x] Do not build residential proxy infrastructure in v1.0.2

## PHASE 14 — Observability & Run Metrics

- [x] Design DuckDB run_metrics table
- [x] Store run timing metrics
- [x] Store discovery/fetch/parse/lead counts
- [x] Store failure categories
- [x] Store browser/external fallback counts
- [x] Store cache hit/miss counts
- [x] Store provider information
- [x] Enable historical performance comparison
- [x] Keep monitoring lightweight and local-first

## PHASE 15 — Batch Processing

- [x] Design bounded batch fetch API
- [x] Reuse concurrency controls
- [x] Preserve per-domain limits
- [x] Preserve failure isolation
- [x] Benchmark batch throughput

## PHASE 16 — Test & Benchmark Matrix

- [x] Normal static HTML workload
- [x] JS-heavy workload
- [x] Empty/thin content workload
- [x] Blocked/rate-limited workload
- [x] Repeated URL workload
- [x] Large URL batch workload
- [x] Generic extraction workload
- [x] Structured-data extraction workload
- [x] Location-quality workload
- [x] Sequential vs concurrent comparison
- [x] HTTP vs browser comparison
- [x] Native vs external-provider comparison
- [x] Cache vs no-cache comparison

## PHASE 17 — Documentation & Public API

- [x] Document acquisition strategies
- [x] Document provider configuration
- [x] Document browser requirements
- [x] Document crawl limits
- [x] Document caching behavior
- [x] Document external-provider integrations
- [x] Document robots/policy behavior
- [x] Document failure categories
- [x] Document migration/compatibility impact
- [x] Keep README and docs aligned with implemented behavior

## DEFERRED — v1.0.3+

- [ ] Background job queue
- [ ] Webhook delivery
- [ ] Persistent browser sessions
- [ ] Advanced browser workflows
- [ ] AI-first extraction/agent workflows
- [ ] Large-scale distributed crawling
- [ ] Extensive JustDial parser
- [ ] Extensive OLX parser
- [ ] Residential proxy rotation
- [ ] In-house CAPTCHA solving
- [ ] Firecrawl-scale cloud orchestration

## v1.0.2 Architecture Decision

The locked architectural direction is:

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
Lead Quality + Location Validation
        ↓
Normalize + Deduplicate
        ↓
DuckDB
        +
Run Metrics
```

## v1.0.2 Non-Negotiable Principles

- [ ] HTTP remains the cheapest/default acquisition path
- [ ] Browser rendering is fallback-driven, not browser-first
- [ ] External scraping services remain optional adapters
- [ ] Proxy infrastructure is evidence-driven, not assumed
- [ ] Deterministic extraction remains preferred over AI extraction
- [ ] Existing public APIs remain compatible wherever practical
- [ ] Performance decisions require benchmark evidence
- [ ] Site-specific implementations require demonstrated value
- [ ] Robots and project policy are never silently bypassed
- [ ] Local/self-hosted operation remains a first-class mode

## R&D Status

- **Roadmap:** LOCKED
- **Implementation:** NOT STARTED
- **Current priority:** Phase 0 — baseline benchmark and validation
- **Next gate:** baseline evidence → implementation sequence confirmation
