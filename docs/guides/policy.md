# Public-Web and Robots Policy

This project is intended for public-web scraping only.

The engine does not provide mechanisms for:

- login bypass
- CAPTCHA bypass
- private-page access
- authentication bypass
- access-control circumvention

Before fetching a page, the fetcher checks the site's `robots.txt` policy. Where supported, crawl-delay directives are respected.

Request throttling and per-domain limits are also available to reduce unnecessary request pressure.

A robots check failure is treated as a fetch failure rather than silently assuming permission.
