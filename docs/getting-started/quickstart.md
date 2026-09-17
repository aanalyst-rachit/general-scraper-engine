# Quick Start

## Brave Search

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"

python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh"
```

Add requirements and a result limit:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --requirements "homeopathy" \
  --limit 20
```

## SearXNG

```bash
python run_scraper.py \
  --provider searxng \
  --searxng-url "http://127.0.0.1:8080" \
  --keyword dentist \
  --location "Shahjahanpur, Uttar Pradesh"
```

The default SearXNG URL is `http://127.0.0.1:8080`.

## Direct Sources

Specialized source adapters can be selected directly with `--source`.

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
