# Limitations

This is a public-web lead scraper, not a universal crawler.

Results depend on:

- search-provider availability and ranking
- search API configuration
- public page availability
- page structure and markup quality
- robots policies
- network conditions
- rate limits
- information exposed by each website

Not every website exposes structured business information. Some pages also require JavaScript rendering or browser interaction that a plain HTTP request cannot provide.

## Direct Source Limitations

The CLI supports specialized direct-source adapters for Google Maps and Justdial.

- `GoogleMapsAdapter` uses the Google Maps Places API and requires an API key.
- `GoogleMapsBrowserAdapter` uses Playwright browser acquisition.
- `JustdialBrowserAdapter` uses Playwright browser acquisition.

Direct-source adapters return normalized `Lead` records directly rather than using the generic discovery and page-parsing pipeline.

Source availability and extracted fields depend on what the selected public source exposes. Missing source fields are not fabricated.

## Browser Requirements

`BrowserFetcher` provides optional Playwright-based browser acquisition. The core package does not install Playwright automatically.

Install the optional browser dependency with:

```bash
pip install playwright
playwright install chromium
```

Browser acquisition runs Chromium headlessly and supports optional waiting, selector-based waiting, clicking, and bounded scrolling.

Browser concurrency defaults to 2. Browser acquisition can fail when Playwright or its Chromium browser binary is unavailable.

## Crawl Limits

`SiteCrawler` is intentionally bounded to prevent an unrestricted crawl.

The default limits are:

- maximum pages: 10
- maximum depth: 1
- global crawler concurrency: 1

By default, crawling remains on the seed URL domain. Additional domains can be explicitly allowed, and include/exclude URL patterns can further constrain the crawl.

Failed page acquisitions do not terminate the complete crawl. Individual failures are isolated and the crawler continues with other eligible URLs.

## Caching Behavior

Fetch results can be cached in DuckDB through `FetchCache` and `CachedFetcher`. Cache keys include the canonical URL and acquisition strategy.

The default fetch-cache policies are:

| Policy | TTL |
| --- | --- |
| `general` | 24 hours |
| `high_change` | 1 hour |
| `stable` | 7 days |

Only successful fetched pages are cached by `CachedFetcher`. Expired entries are treated as cache misses and are not returned to the acquisition pipeline.

The default fetch-cache database is `data/fetch_cache.duckdb`.

## External Provider Limitations

External acquisition providers are optional integrations. Their availability, response behavior, quotas, pricing, and service-specific restrictions remain outside the scraper engine.

The current adapters are `FirecrawlProvider`, `ScrapeDoProvider`, and `ScrapingdogProvider`.

These providers are programmatic acquisition components rather than CLI discovery-provider choices.

## Public-Web Boundary

The engine is designed for publicly accessible web content. It does not provide login handling, CAPTCHA solving, private-data access, or mechanisms intended to bypass access controls.

Native HTTP acquisition checks robots policy before requesting pages. Request delays, crawl delays, per-domain request limits, and bounded concurrency can be applied through the acquisition and concurrency layers.

## Compatibility

The existing `general-scraper` CLI and `python run_scraper.py` entry point remain available.

Programmatic callers can use `scraper.engine.scrape()` or construct `ScraperEngine` directly. Existing HTTP-oriented acquisition can continue through the HTTP fetcher adapter while browser and external acquisition remain composable alternatives.
