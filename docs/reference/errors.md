# Error Handling

The scraper is designed so that one problematic page does not normally terminate an entire scrape.

## Tracked Failures

- HTTP 4xx responses
- HTTP 5xx responses
- Request timeouts
- Redirect/fetch failures
- robots-policy failures
- Non-HTML pages
- Malformed pages
- Invalid JSON-LD
- Parser failures

## Scrape Results

`ScrapeResult` exposes discovered pages, successful fetches, fetch failures, parse failures and final leads.
