# Discovery Providers

## Brave Search

`BraveSearchProvider` uses the Brave Search Web API.

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

The provider also supports explicit API-key injection when used programmatically.

## SearXNG

`SearXNGProvider` connects to a SearXNG server using its JSON search endpoint.

```bash
python run_scraper.py \\
  --provider searxng \\
  --searxng-url "http://127.0.0.1:8080" \\
  --keyword restaurant
```

Because discovery is provider-based, the core scraper does not depend on one specific search service.
