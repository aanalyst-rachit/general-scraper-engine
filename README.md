# General Scraper Engine

A general-purpose Python web lead scraper for discovering and extracting structured business or professional leads from public web pages.

The engine accepts a keyword, optional location, and optional requirements, then runs a pipeline of:

**Discovery → Fetch → Parse → Relevance → Normalize → Quality Check → Deduplicate → Output**

It is designed for public-web research and lead-generation workflows without requiring login or bypassing access controls.

## Features

- Keyword-based public-web discovery
- Optional location targeting
- Optional requirements matching
- Replaceable discovery-provider abstraction
- Brave Search provider
- SearXNG provider
- HTTP/HTTPS page fetching
- Redirect handling
- Timeout and HTTP-error handling
- Retry and throttling policies
- `robots.txt` checking
- Crawl-delay support
- Per-domain request limits
- JSON-LD / Schema.org extraction
- Meta/OpenGraph/title fallbacks
- Phone, email, address, website and location extraction
- Keyword, location, category and requirements relevance filtering
- Lead normalization
- Identity-based lead deduplication
- Duplicate-record merging
- Source URL preservation
- Lead quality validation
- Fetch and parse failure tracking
- JSON and CSV output
- Optional DuckDB persistence
- Automated pytest coverage

## Requirements

- Python 3.12+
- Internet access for live web discovery/fetching
- A Brave Search API key when using the Brave provider
- A running SearXNG instance when using the SearXNG provider

## Installation

Clone or copy the project and create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The project can be installed as a Python package with `pip install .`, which also installs the `general-scraper` CLI entry point. Running `python run_scraper.py` directly from the repository remains supported for development.

## Quick Start

### Brave Search

Set the Brave Search API key:

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

Run a search:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh"
```

Add requirements:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --requirements "homeopathy" \
  --limit 20
```

The command prints discovered leads and a summary containing discovered pages, fetched pages, fetch failures and parse failures.

### SearXNG

Start a SearXNG instance and provide its base URL:

```bash
python run_scraper.py \
  --provider searxng \
  --searxng-url "http://127.0.0.1:8080" \
  --keyword dentist \
  --location "Shahjahanpur, Uttar Pradesh"
```

The default SearXNG URL is:

```text
http://127.0.0.1:8080
```

## CLI Usage

Show all available options:

```bash
python run_scraper.py --help
```

Main options:

| Option           | Required | Default                 | Description                                      |
| ---------------- | -------- | ----------------------- | ------------------------------------------------ |
| `--keyword`      | Yes      | —                       | Search keyword, such as `doctor` or `restaurant` |
| `--location`     | No       | empty                   | Target location                                  |
| `--requirements` | No       | empty                   | Additional requirements                          |
| `--limit`        | No       | `50`                    | Maximum discovered pages to process              |
| `--provider`     | No       | `brave`                 | Discovery provider: `brave` or `searxng`         |
| `--searxng-url`  | No       | `http://127.0.0.1:8080` | SearXNG base URL                                 |
| `--json`         | No       | —                       | Write leads to a JSON file                       |
| `--csv`          | No       | —                       | Write leads to a CSV file                        |
| `--save-db`      | No       | disabled                | Persist leads to DuckDB                          |
| `--db-path`      | No       | `data/leads.duckdb`     | DuckDB database path                             |

The keyword must not be empty and the limit must be a positive integer.

## Output

### Terminal

The default terminal output contains:

* Lead count
* Lead name
* Category
* Location
* Address
* Phone
* Email
* Website
* Source name
* Source URL
* Discovery/fetch/parse summary

### JSON

Write structured results to JSON:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --json results.json
```

The JSON file contains an array of serialized `Lead` records.

### CSV

Write structured results to CSV:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --csv results.csv
```

Nested fields such as social profiles and raw/extra data are serialized as JSON strings inside the CSV.

### DuckDB

Persistence is optional:

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --save-db
```

Use a custom database path:

```bash
python run_scraper.py \
  --keyword doctor \
  --save-db \
  --db-path data/my-leads.duckdb
```

The repository normalizes leads and uses identity keys to avoid creating duplicate records.

## Architecture

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

### Discovery

`WebDiscovery` builds search queries from the keyword, location and requirements and delegates searches to one or more providers.

The provider abstraction is based on the `DiscoveryProvider` protocol, allowing additional providers to be added without changing the core discovery pipeline.

### Fetching

`PageFetcher` retrieves public HTTP/HTTPS pages and handles:

* redirects
* timeouts
* HTTP errors
* retryable server failures
* non-HTML responses
* robots restrictions
* crawl delays
* request throttling
* per-domain request limits

Individual fetch failures are recorded rather than terminating the complete scrape.

### Parsing

`PageParser` extracts lead information from public HTML.

Structured data is read primarily from JSON-LD / Schema.org. The parser also falls back to:

* meta descriptions
* OpenGraph metadata
* Twitter/title metadata
* visible address elements
* phone patterns
* email patterns

Malformed HTML and invalid JSON-LD are handled defensively.

### Relevance

Candidates can be filtered using:

* keyword relevance
* location relevance
* category relevance
* requirements relevance

This prevents obviously unrelated discovered pages from becoming final leads.

### Normalization and Deduplication

`LeadNormalizer` standardizes:

* text
* names
* phone numbers
* email addresses
* URLs

Identity keys can use available combinations of phone, email, website/name, company/name, address, profession and location.

When duplicate leads are detected, available information is merged and source URLs are preserved.

## Lead Schema

The main `Lead` model contains the following groups of fields.

### Identity

* `name`
* `profession`
* `company_name`
* `category`
* `subcategory`

### Professional / Business

* `designation`
* `specialization`
* `services`
* `description`

### Contact

* `phone`
* `alternate_phone`
* `email`
* `alternate_email`
* `website`

### Address

* `address`
* `location`
* `locality`
* `city`
* `district`
* `state`
* `country`
* `pincode`

### Public Profiles

* `social_profiles`

### Source / Discovery

* `source_url`
* `source_name`
* `source_id`
* `search_context`

### Flexible Data

* `extra`
* `raw_data`

The model can be serialized using `Lead.to_dict()`.

## Programmatic API

The main implementation modules are:

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

Core classes include:

* `Lead`
* `SearchRequest`
* `DiscoveredPage`
* `DiscoveryProvider`
* `WebDiscovery`
* `FetchedPage`
* `PageFetcher`
* `PageParser`
* `LeadNormalizer`
* `LeadQuality`
* `ScraperEngine`
* `ScrapeResult`
* `BraveSearchProvider`
* `SearXNGProvider`
* `DuckDBLeadRepository`

The high-level `scrape()` function in `scraper.engine` provides the main programmatic pipeline entry point.

## Discovery Providers

### Brave Search

`BraveSearchProvider` uses the Brave Search Web API.

Configuration is supplied through:

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

The provider also supports explicit API-key injection when used programmatically.

### SearXNG

`SearXNGProvider` connects to a SearXNG server using its JSON search endpoint.

Example:

```bash
python run_scraper.py \
  --provider searxng \
  --searxng-url "http://127.0.0.1:8080" \
  --keyword restaurant
```

Because discovery is provider-based, the core scraper does not depend on one specific search service.

## Public-Web and Robots Policy

This project is intended for public-web scraping only.

The engine does not provide mechanisms for:

* login bypass
* CAPTCHA bypass
* private-page access
* authentication bypass
* access-control circumvention

Before fetching a page, the fetcher checks the site's `robots.txt` policy. Where supported, crawl-delay directives are respected.

Request throttling and per-domain limits are also available to reduce unnecessary request pressure.

A robots check failure is treated as a fetch failure rather than silently assuming permission.

## Error Handling

The scraper is designed so that one problematic page does not normally terminate an entire scrape.

Tracked failures include:

* HTTP 4xx responses
* HTTP 5xx responses
* request timeouts
* redirects/fetch failures
* robots-policy failures
* non-HTML pages
* malformed pages
* invalid JSON-LD
* parser failures

`ScrapeResult` exposes discovered pages, successful fetches, fetch failures, parse failures and final leads.

## Examples

### Doctors in a city

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 25
```

### Restaurants with JSON output

```bash
python run_scraper.py \
  --keyword restaurant \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 25 \
  --json restaurants.json
```

### Business leads with CSV output

```bash
python run_scraper.py \
  --keyword "real estate agent" \
  --location "Lucknow, Uttar Pradesh" \
  --csv leads.csv
```

### Persistent lead collection

```bash
python run_scraper.py \
  --keyword dentist \
  --location "Shahjahanpur, Uttar Pradesh" \
  --save-db \
  --db-path data/dentists.duckdb
```

## Testing

Run the complete test suite:

```bash
python -m pytest -q
```

The test suite covers discovery, providers, fetching, parsing, normalization, relevance, quality validation, engine behavior, CLI behavior and DuckDB persistence.

Python compilation can also be checked with:

```bash
python -m compileall scraper run_scraper.py
```

## Limitations

This is a public-web lead scraper, not a universal crawler.

Results depend on:

* search-provider availability and ranking
* search API configuration
* public page availability
* page structure and markup quality
* robots policies
* network conditions
* rate limits
* information exposed by each website

Not every website exposes structured business information, and some pages may require JavaScript rendering that the current HTTP/HTML pipeline does not execute.

The CLI is available both as the installed `general-scraper` command and as `python run_scraper.py` when running directly from the repository.

## Project Status

The core scraping pipeline, documentation, packaging, and release validation are implemented through Phase 17.

Current development phase:

**Phase 17 — Final Test & Release Audit**

The project is undergoing final V1 release checks.

## License

See [LICENSE](LICENSE) for the project license.
