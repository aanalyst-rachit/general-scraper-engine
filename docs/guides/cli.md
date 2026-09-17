# CLI Usage

Show all available options:

```bash
python run_scraper.py --help
```

## General Options

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| `--keyword` | Yes | — | Search keyword |
| `--location` | No | empty | Target location |
| `--requirements` | No | empty | Additional requirements |
| `--category` | No | empty | Exact category filter |
| `--limit` | No | `50` | Maximum results to process |
| `--provider` | No | `brave` | Discovery provider: `brave` or `searxng` |
| `--searxng-url` | No | `http://127.0.0.1:8080` | SearXNG base URL |

## Source Selection

The CLI supports the normal discovery pipeline and specialized direct-source adapters.

| Option | Values | Description |
| --- | --- | --- |
| `--source` | `discovery`, `google-maps`, `google-maps-browser`, `justdial-browser` | Select the acquisition source |
| `--google-maps-api-key` | API key | Google Maps Places API key |
| `--source-timeout` | seconds | Timeout for direct-source requests |
| `--source-wait` | seconds | Browser wait time for direct-source browser adapters |

### Google Maps Browser

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

### Google Maps Places API

```bash
export GOOGLE_MAPS_API_KEY="your-api-key"

python run_scraper.py \
  --source google-maps \
  --google-maps-api-key "$GOOGLE_MAPS_API_KEY" \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

### Justdial Browser

```bash
python run_scraper.py \
  --source justdial-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

## Browser Fetching

Browser acquisition options:

| Option | Default | Description |
| --- | --- | --- |
| `--fetcher` | `default` | Fetcher strategy: `default`, `browser`, `firecrawl`, `scrape-do`, or `scrapingdog` |
| `--browser-timeout` | — | Browser fetch timeout |
| `--browser-wait` | — | Browser wait time |
| `--wait-for-selector` | — | Wait for a CSS selector |
| `--scroll-steps` | — | Number of browser scroll steps |
| `--click-selector` | — | CSS selector to click |
| `--max-concurrency` | — | Maximum acquisition concurrency |

## Output and Persistence

| Option | Default | Description |
| --- | --- | --- |
| `--json` | — | Write leads to JSON |
| `--csv` | — | Write leads to CSV |
| `--save-db` | disabled | Persist leads to DuckDB |
| `--db-path` | `data/leads.duckdb` | DuckDB database path |

Example with CSV output and DuckDB persistence:

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5 \
  --csv restaurant-results.csv \
  --save-db \
  --db-path data/restaurants.duckdb
```

## Validation

The keyword must not be empty and the limit must be a positive integer.
