# Installation

## Requirements

- Python 3.12+
- Internet access for live web discovery/fetching
- A Brave Search API key when using the Brave provider
- A running SearXNG instance when using the SearXNG provider

## Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Dependencies

```bash
pip install -r requirements.txt
```

The project can also be installed as a Python package:

```bash
pip install .
```

This installs the `general-scraper` CLI entry point.

## Optional Browser Sources

Google Maps Browser and Justdial Browser source adapters use Playwright.

Install the browser dependency and Chromium with:

```bash
pip install playwright
playwright install chromium
```

The Google Maps Places API source adapter requires a Google Maps API key. It can be supplied through `--google-maps-api-key` or the `GOOGLE_MAPS_API_KEY` environment variable.
