# Limitations

This is a public-web lead scraper, not a universal crawler.

Results depend on:

- search-provider availability and ranking
- search API configuration
- public page availability
- page structure and markup quality
- robots policies
- network conditions
- rate limits
- information exposed by each website

Not every website exposes structured business information, and some pages may require JavaScript rendering that the current HTTP/HTML pipeline does not execute.

The CLI is available both as the installed `general-scraper` command and as `python run_scraper.py` when running directly from the repository.
