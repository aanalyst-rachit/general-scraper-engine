# Public-Web and Robots Policy

This project is intended for public-web scraping only.

The engine does not provide mechanisms for:

- login bypass
- CAPTCHA bypass
- private-page access
- authentication bypass
- access-control circumvention

## Robots Policy

Before native HTTP acquisition, `PageFetcher` checks the target sites `robots.txt` policy for the configured user agent.

If `robots.txt` disallows the requested URL, the fetch is rejected with a robots-policy failure rather than being attempted.

If the robots policy cannot be loaded or evaluated, the fetch is treated as a policy-check failure. The engine does not silently assume permission.

Robots rules are cached in memory by `PageFetcher` for the lifetime of that fetcher instance.

## Crawl and Request Delays

`PageFetcher` supports an explicit `request_delay` between requests to the same origin.

If the site provides a supported `crawl-delay` directive, the effective delay is the greater of the configured request delay and the robots crawl delay.

Delay state is tracked per origin and synchronized so concurrent requests do not intentionally bypass the configured delay.
## Per-Domain Request Limits

`PageFetcher` can enforce `max_requests_per_domain` to bound the number of native HTTP request attempts made to a domain.

The limit is checked for each request attempt, including retry attempts. When the configured limit is reached, the fetch returns a request-limit failure instead of issuing another request.

## Retry Policy

Retries are disabled by default (`max_retries=0`). When enabled, retryable conditions include:

- HTTP 5xx responses
- request timeouts
- other `httpx.HTTPError` failures

HTTP 4xx responses are returned immediately and are not retried.

An optional `retry_backoff` can add an increasing delay before retry attempts.

Non-HTML responses are rejected rather than passed to the HTML parsing pipeline.

## Failure Handling

Policy and acquisition failures are represented as `FetchedPage` failures and are isolated from other URLs in the scrape run.

The engine maps policy, request-limit, access-blocked, rate-limit, authentication, server-error, timeout, and invalid-response conditions into structured failure categories where applicable.
## External Acquisition Policy

`PolicyAwareExternalFetcher` applies the same robots and request-delay checks before invoking an external acquisition provider.

The wrapper validates the URL, checks whether robots policy permits fetching, applies the configured request/crawl delay, and only then calls the external provider.

This keeps public-web policy enforcement separate from individual third-party provider implementations.

External providers remain subject to their own service terms, quotas, availability, and restrictions.

## Browser Acquisition

Browser acquisition is an optional acquisition strategy. The browser fetcher is subject to the same public-web boundary but does not replace the native HTTP fetchers robots implementation automatically.

Applications that require policy enforcement around browser acquisition should compose the browser strategy with the appropriate policy layer.

The engine does not use browser acquisition to bypass authentication, CAPTCHA, robots restrictions, or other access controls.
