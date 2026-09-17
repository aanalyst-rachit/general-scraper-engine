# General Scraper Engine — v1.0.3 Release Notes

## Release Status

- Version: `1.0.3`
- Status: Release Candidate / Final Audit
- Previous release: `1.0.2`

## Release Summary

v1.0.3 extends the CLI with specialized direct-source acquisition for Google Maps and Justdial while keeping results on the common `Lead` model.

The release also adds direct-source category filtering, JSON/CSV/DuckDB output support, browser-source documentation, and expanded CLI/source-adapter validation.

## Completed Capabilities

- SourceAdapter and SourceAdapterRegistry integration
- Google Maps Places API source adapter
- Google Maps browser source adapter
- Justdial browser source adapter
- Direct-source CLI selection through `--source`
- Exact normalized category filtering through `--category`
- Direct-source JSON output
- Direct-source CSV output
- Direct-source DuckDB persistence
- Lead-level location validation and quality checks for direct sources
- Direct-source normalization and deduplication
- Playwright installation documentation for browser sources
- Updated CLI, provider, architecture, API, schema, testing, limitations, and contributing documentation

## Validation Evidence

- Full test suite baseline: `450 passed, 3 skipped`
- CLI tests: `21 passed`
- Google Maps browser adapter tests: `8 passed`
- Real Google Maps browser CLI acquisition verified
- Google Maps browser CSV output verified
- Google Maps browser DuckDB persistence verified
- Direct-source category filter verified with `Chinese restaurant`

## Known Remaining Work

- Direct-source `--requirements` filtering remains a known limitation and is deferred.
- Justdial real-world acquisition requires further validation because the tested public request encountered an HTTP/2 protocol error.
- Brave API real-world validation remains deferred.
- OLX specialized parser remains incomplete.
- LinkedIn specialized parser remains incomplete.

## Scope Boundaries

This release remains focused on public-web lead acquisition. Login bypass, CAPTCHA solving, private or access-controlled data extraction, and access-control circumvention remain outside the release scope.

Browser source adapters acquire publicly accessible source pages and do not fabricate missing source fields.

## Release Verification

- [ ] Final tracker review completed
- [ ] Final test suite passes
- [ ] Compile check passes
- [ ] Documentation reviewed
- [ ] Version metadata updated to `1.0.3`
- [ ] Git commit created
- [ ] Git tag `v1.0.3` created
- [ ] Package published and verified
- [ ] GitHub release published
