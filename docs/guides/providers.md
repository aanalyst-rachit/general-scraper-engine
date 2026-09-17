# Providers

## Discovery Providers

The engine separates web discovery from page acquisition. A discovery provider returns `DiscoveredPage` records that are later processed by the acquisition and extraction pipeline.

## Brave Search

`BraveSearchProvider` uses the Brave Search Web API.

Configure the API key through the environment:

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

The API key can also be supplied explicitly when constructing `BraveSearchProvider`.

```python
from scraper.providers.brave import BraveSearchProvider

provider = BraveSearchProvider(api_key="your-api-key")
```

The default search country is `IN` and the default search language is `en`. Both can be overridden through the provider constructor.

The provider requests at most 20 results from the Brave API per search call and deduplicates URLs before returning results.

## SearXNG

`SearXNGProvider` connects to a SearXNG instance through its JSON search endpoint.

The default base URL is `http://127.0.0.1:8080`.

```bash
python run_scraper.py \
  --provider searxng \
  --searxng-url "http://127.0.0.1:8080" \
  --keyword restaurant
```

The provider follows SearXNG result pages until the requested limit is reached or no new results are returned.

## Source Adapters

Source-specific adapters provide direct acquisition from supported public sources and return normalized `Lead` records.

Current direct-source adapters are:

- `GoogleMapsAdapter` — Google Maps Places API
- `GoogleMapsBrowserAdapter` — Google Maps browser acquisition through Playwright
- `JustdialBrowserAdapter` — Justdial browser acquisition through Playwright

These adapters are selected through the CLI `--source` option.

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

Direct-source results use the common `Lead` model and can be written to JSON, CSV, or DuckDB.

## External Acquisition Providers

External providers implement the provider-neutral `ExternalFetcher` contract. They acquire page content through third-party scraping services rather than the native HTTP fetcher.

Current adapters are:

- `FirecrawlProvider`
- `ScrapeDoProvider`
- `ScrapingdogProvider`

These integrations are optional and are configured programmatically. They are separate from the CLI discovery-provider selection.

## Firecrawl

`FirecrawlProvider` uses the Firecrawl scrape API and requests HTML output.

```bash
export FIRECRAWL_API_KEY="your-api-key"
```

The default client timeout is 30 seconds. A per-request timeout can be supplied through `ExternalFetchRequest`.

## Scrape.do

`ScrapeDoProvider` uses the Scrape.do API.

```bash
export SCRAPE_DO_API_KEY="your-api-key"
```

The default client timeout is 30 seconds. `ExternalFetchRequest(render=True)` enables the provider render option.

## Scrapingdog

`ScrapingdogProvider` uses the Scrapingdog scrape API.

```bash
export SCRAPINGDOG_API_KEY="your-api-key"
```

The default client timeout is 60 seconds. `ExternalFetchRequest(render=True)` enables dynamic rendering.

## Policy-Aware External Acquisition

`PolicyAwareExternalFetcher` wraps an external provider and applies the configured acquisition policy before making the provider request.

The wrapper checks that the URL is valid, verifies the configured fetch policy, and applies the configured request delay before invoking the external provider.

This keeps policy enforcement separate from individual third-party provider adapters.

## Custom Providers

Discovery providers implement the `DiscoveryProvider` contract, while page-acquisition providers implement `AcquisitionStrategy` or `ExternalFetcher` as appropriate.

This allows additional discovery or acquisition services to be added without changing the core engine pipeline.

Provider failures are returned through the normal result and failure-measurement paths rather than requiring the complete scrape run to terminate.

## Provider Selection

The CLI exposes `brave` and `searxng` as discovery-provider choices.

The CLI also exposes `google-maps`, `google-maps-browser`, and `justdial-browser` as direct-source choices.

External acquisition providers are available as programmatic components and can be composed with the acquisition layer when a caller needs third-party scraping.
