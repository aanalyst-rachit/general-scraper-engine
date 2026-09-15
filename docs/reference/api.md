# Programmatic API

## Package Structure

```text
scraper/
├── models.py
├── discovery.py
├── fetcher.py
├── parser.py
├── relevance.py
├── normalizer.py
├── quality.py
├── engine.py
├── providers/
│   ├── brave.py
│   └── searxng.py
└── database/
    ├── repository.py
    └── duckdb.py
```

## Core Classes

- `Lead`
- `SearchRequest`
- `DiscoveredPage`
- `DiscoveryProvider`
- `WebDiscovery`
- `FetchedPage`
- `PageFetcher`
- `PageParser`
- `LeadNormalizer`
- `LeadQuality`
- `ScraperEngine`
- `ScrapeResult`
- `BraveSearchProvider`
- `SearXNGProvider`
- `DuckDBLeadRepository`

## Main Entry Point

The high-level `scrape()` function in `scraper.engine` provides the main programmatic pipeline entry point.
