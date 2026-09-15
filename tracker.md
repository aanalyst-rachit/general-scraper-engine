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

- [ ] Introduce bounded async execution
- [ ] Define global concurrency limit
- [ ] Define per-domain concurrency limit
- [ ] Define provider concurrency limit
- [ ] Ensure robots/request-delay policy remains enforced
- [ ] Benchmark sequential vs concurrent fetch performance
- [ ] Avoid unbounded asyncio tasks

## PHASE 5 — Discovery Provider Routing

- [ ] Preserve DiscoveryProvider protocol
- [ ] Add provider router/policy layer
- [ ] Support primary provider and explicit fallback providers
- [ ] Categorize provider failures: no-results, timeout, auth, rate-limit, server-error, invalid-response
- [ ] Define quality-based fallback policy separately from failure fallback
- [ ] Preserve existing query deduplication
- [ ] Preserve existing per-run URL deduplication
- [ ] Evaluate SearXNG / Brave as current native providers
- [ ] Evaluate optional external search providers before implementation

## PHASE 6 — Discovery Cache

- [ ] Design discovery cache schema
- [ ] Define canonical cache key including provider/config/query/search parameters
- [ ] Store creation and expiry timestamps
- [ ] Define TTL policy by discovery source/use case
- [ ] Implement DuckDB-backed discovery cache only after benchmark validates benefit
- [ ] Measure cache hit/miss behavior

## PHASE 7 — Fetch Cache

- [ ] Design fetch cache schema
- [ ] Include canonical URL, acquisition strategy, status, content type, content hash, timestamps, and metadata
- [ ] Define cache invalidation/TTL policy
- [ ] Evaluate HTML storage size before committing to DuckDB blob storage
- [ ] Implement cache only after storage/performance R&D
- [ ] Measure repeated-fetch latency reduction

## PHASE 8 — Content & Extraction Layer

- [ ] Introduce content-quality classification
- [ ] Preserve existing generic parser
- [ ] Add structured-data extraction path (Schema.org/JSON-LD)
- [ ] Define extraction strategy interface
- [ ] Introduce parser/extractor registry
- [ ] Route site-specific parser before generic fallback
- [ ] Keep deterministic extraction ahead of optional AI extraction
- [ ] Evaluate Markdown representation as an optional normalized content format

## PHASE 9 — Lead Quality & Relevance

- [ ] Audit existing LeadQuality and relevance behavior
- [ ] Define requested-location vs extracted-location validation
- [ ] Detect conflicting location evidence
- [ ] Define lead quality scoring dimensions
- [ ] Measure lead quality separately from fetch success
- [ ] Preserve current Lead model compatibility
- [ ] Avoid accepting technically valid but geographically irrelevant leads

## PHASE 10 — Map & Crawl

- [ ] Design bounded site-map operation
- [ ] Discover internal URLs from a seed URL
- [ ] Canonicalize URLs
- [ ] Deduplicate URLs
- [ ] Support max pages
- [ ] Support max depth
- [ ] Support allowed domains
- [ ] Support include/exclude URL patterns
- [ ] Respect robots policy
- [ ] Reuse acquisition and extraction layers
- [ ] Implement bounded crawler rather than Firecrawl-scale distributed crawling

## PHASE 11 — External Scraping Provider Adapters

- [ ] Define ExternalFetcher interface
- [ ] Define provider-neutral request/response contract
- [ ] Evaluate Firecrawl integration
- [ ] Evaluate Scrape.do integration
- [ ] Evaluate Scrapingdog integration
- [ ] Keep external providers optional
- [ ] Do not make any external provider mandatory for local/self-hosted usage
- [ ] Ensure external providers cannot silently bypass robots/policy decisions

## PHASE 12 — Specialized Source Adapters

- [ ] Define SourceAdapter architecture
- [ ] Evaluate Google Search adapter
- [ ] Evaluate Google Maps adapter
- [ ] Compare official APIs vs direct browser scraping vs external providers
- [ ] Prefer official API where cost, coverage, and terms justify it
- [ ] Add specialized adapter only when benchmark/use-case evidence justifies maintenance cost
- [ ] Defer large collections of site-specific parsers

## PHASE 13 — Anti-Blocking / Operational Resilience

- [ ] Build failure taxonomy first
- [ ] Detect 403 / 429 / CAPTCHA / bot-block / challenge pages
- [ ] Tune retries and throttling from observed evidence
- [ ] Evaluate browser fallback before proxy infrastructure
- [ ] Evaluate external provider fallback before owning proxy infrastructure
- [ ] Residential proxy support remains conditional
- [ ] Do not build an in-house CAPTCHA-solving system
- [ ] Do not build residential proxy infrastructure in v1.0.2

## PHASE 14 — Observability & Run Metrics

- [ ] Design DuckDB run_metrics table
- [ ] Store run timing metrics
- [ ] Store discovery/fetch/parse/lead counts
- [ ] Store failure categories
- [ ] Store browser/external fallback counts
- [ ] Store cache hit/miss counts
- [ ] Store provider information
- [ ] Enable historical performance comparison
- [ ] Keep monitoring lightweight and local-first

## PHASE 15 — Batch Processing

- [ ] Design bounded batch fetch API
- [ ] Reuse concurrency controls
- [ ] Preserve per-domain limits
- [ ] Preserve failure isolation
- [ ] Benchmark batch throughput

## PHASE 16 — Test & Benchmark Matrix

- [ ] Normal static HTML workload
- [ ] JS-heavy workload
- [ ] Empty/thin content workload
- [ ] Blocked/rate-limited workload
- [ ] Repeated URL workload
- [ ] Large URL batch workload
- [ ] Generic extraction workload
- [ ] Structured-data extraction workload
- [ ] Location-quality workload
- [ ] Sequential vs concurrent comparison
- [ ] HTTP vs browser comparison
- [ ] Native vs external-provider comparison
- [ ] Cache vs no-cache comparison

## PHASE 17 — Documentation & Public API

- [ ] Document acquisition strategies
- [ ] Document provider configuration
- [ ] Document browser requirements
- [ ] Document crawl limits
- [ ] Document caching behavior
- [ ] Document external-provider integrations
- [ ] Document robots/policy behavior
- [ ] Document failure categories
- [ ] Document migration/compatibility impact
- [ ] Keep README and docs aligned with implemented behavior

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
