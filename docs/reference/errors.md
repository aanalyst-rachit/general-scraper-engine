# Error Handling

The scraper is designed so that one problematic page does not normally terminate an entire scrape.

## Tracked Failures

Fetch failures and parse failures are recorded per URL. A failure for one candidate is isolated from other candidates in the same scrape run.

Fetch failures may originate from HTTP acquisition, robots policy, request limits, response validation, or transport errors.

Parse failures are recorded when a parser raises an exception or returns no lead for an otherwise successfully fetched page.

## Fetch Failure Categories

`ScrapeResult.fetch_failures` contains `FetchFailure` records with the affected URL and the original fetch error.

The engine maps common fetch errors into the following categories for run-level measurements:

| Category | Meaning |
| --- | --- |
| `timeout` | The HTTP request exceeded its configured timeout. |
| `policy` | The URL was blocked by `robots.txt` policy. |
| `request-limit` | The configured per-domain request-attempt limit was reached. |
| `auth` | The response indicates HTTP 401 authentication is required. |
| `access-blocked` | The response indicates HTTP 403 access is blocked. |
| `rate-limit` | The response indicates HTTP 429 rate limiting. |
| `server-error` | The response is an HTTP 5xx server error. |
| `invalid-response` | The failure does not match another specific fetch category, including non-HTML or other invalid responses. |

## Content Quality Categories

`ContentQualityClassifier` classifies acquired pages before downstream parsing and browser fallback decisions.

| Category | Meaning |
| --- | --- |
| `valid_content` | The page contains sufficient usable content or useful structured data. |
| `empty_content` | The response contains no usable HTML/body content. |
| `thin_content` | The page contains very little body text. |
| `js_shell` | The page appears to be a JavaScript application shell with insufficient rendered content. |
| `error_page` | The response status or page markers indicate an error page. |
| `block_page` | Page content contains common bot, CAPTCHA, or access-blocking markers. |
| `access_blocked` | The HTTP response is 403 access blocked. |
| `rate_limited` | The HTTP response is 429 rate limited. |
| `auth_required` | The HTTP response is 401 authentication required. |

Only `empty_content`, `thin_content`, and `js_shell` are classified as requiring browser fallback by the content-quality classifier.

## Scrape Results

`ScrapeResult` exposes discovered pages, successful fetches, fetch failures, parse failures and final leads.

The result also tracks quality-check counts for accepted and rejected leads.

Fetch and parse failures do not automatically terminate the complete run. The engine continues processing other eligible candidates and preserves the individual failure records for inspection.

## Failure and Retry Behavior

Native HTTP retries are disabled by default. When configured, HTTP 5xx responses, request timeouts, and other `httpx.HTTPError` failures may be retried according to the fetcher retry configuration.

HTTP 4xx responses are not retried by the native fetcher. Non-HTML responses are rejected before HTML parsing.
