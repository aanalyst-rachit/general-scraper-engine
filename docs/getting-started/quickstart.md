# Quick Start

## Brave Search

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"

python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh"
```

Add requirements and a result limit:

```bash
python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --requirements "homeopathy" \\
  --limit 20
```

## SearXNG

```bash
python run_scraper.py \\
  --provider searxng \\
  --searxng-url "http://127.0.0.1:8080" \\
  --keyword dentist \\
  --location "Shahjahanpur, Uttar Pradesh"
```

The default SearXNG URL is `http://127.0.0.1:8080`.
