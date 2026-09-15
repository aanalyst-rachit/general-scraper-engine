# Architecture

```text
CLI
 │
 ▼
SearchRequest
 │
 ▼
WebDiscovery
 │
 ├── BraveSearchProvider
 └── SearXNGProvider
 │
 ▼
DiscoveredPage
 │
 ▼
PageFetcher
 │
 ▼
FetchedPage
 │
 ▼
PageParser
 │
 ▼
Lead
 │
 ▼
Relevance Filters
 │
 ▼
LeadNormalizer
 │
 ▼
LeadQuality
 │
 ▼
Deduplication / Merge
 │
 ├── Terminal output
 ├── JSON
 ├── CSV
 └── Optional DuckDB repository
```

## Discovery

`WebDiscovery` builds search queries from keyword, location and requirements and delegates searches to providers.

The `DiscoveryProvider` protocol allows additional providers without changing the core discovery pipeline.

## Fetching

`PageFetcher` handles redirects, timeouts, HTTP errors, retryable failures, non-HTML responses, robots restrictions, crawl delays, throttling and per-domain limits.

Individual fetch failures are recorded rather than terminating the complete scrape.

## Parsing

`PageParser` extracts lead information from public HTML, primarily using JSON-LD / Schema.org with meta, OpenGraph, title, address, phone and email fallbacks.

Malformed HTML and invalid JSON-LD are handled defensively.

## Relevance

Candidates can be filtered using keyword, location, category and requirements relevance.

## Normalization and Deduplication

`LeadNormalizer` standardizes text, names, phone numbers, email addresses and URLs.

Identity keys use available combinations of phone, email, website/name, company/name, address, profession and location. Duplicate leads are merged and source URLs preserved.
