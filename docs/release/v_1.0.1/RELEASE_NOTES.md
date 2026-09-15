# General Scraper Engine — v1.0.1 Release

## Release Status

- Version: `1.0.1`
- Release date: `2026-09-15`
- Status: Published and verified

## V1 Completion

All V1 tracker phases are complete.

- Foundation and data model
- Provider-based public-web discovery
- Fetching, redirects, timeouts, HTTP errors, retries and crawl policy
- robots.txt handling and public-web access rules
- JSON-LD / Schema.org and fallback parsing
- Normalization and lead deduplication
- Relevance filtering and result quality checks
- CLI and structured terminal output
- Real public-web smoke testing
- Robustness and failure handling
- Documentation and examples
- Python packaging and CLI entry point
- Final test and release audit

## Release Artifacts

- Git commit: `b0f20f3` — `release: v1.0.1`
- Git tag: `v1.0.1`
- GitHub Release: published
- PyPI package: `general-scraper-engine==1.0.1`
- PyPI artifacts: wheel and source distribution

## Verification

The v1.0.1 package was successfully uploaded to PyPI and verified with HTTP 200. The published package reports version `1.0.1` and contains two release artifacts.

The Git repository was verified at commit `b0f20f3`, with tag `v1.0.1` at HEAD. The GitHub Release is published, not a draft, and not a prerelease.

## Release Automation

Release mechanics are handled by `release.py`, covering package build, validation, Git commit/tag/push, GitHub Release creation, PyPI upload, and verification.

Project tracker, documentation, and other manual project housekeeping remain manual by design.

## Scope

V1 remains limited to public-web lead discovery. It does not include login, CAPTCHA bypass, private-page access, authentication, UI/dashboard functionality, or PyLage integration.
