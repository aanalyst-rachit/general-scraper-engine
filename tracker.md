# General Scraper Engine — V1 Tracker

## Project Goal

Build a general-purpose public-web lead scraper engine that accepts a keyword, location, and optional requirements, discovers relevant public web pages, extracts lead data, normalizes and deduplicates the results, and outputs structured leads.

## Scope

- General-purpose web lead discovery
- Public web pages only
- Keyword + location + optional requirements
- Discovery → Fetch → Parse → Normalize → Deduplicate → Output
- No login, CAPTCHA, private-page, or access-control bypass
- No UI, dashboard, database, CRM, or authentication in V1
- No PyLage integration in V1

## Roadmap

### Phase 0 — Foundation
- [x] Create project structure
- [x] Create Python virtual environment
- [x] Install core dependencies

### Phase 1 — Data Model
- [x] Create Lead model
- [x] Define structured lead fields

### Phase 2 — Discovery Abstraction
- [x] Create SearchRequest
- [x] Create DiscoveredPage
- [x] Create DiscoveryProvider protocol
- [x] Create WebDiscovery
- [x] Add query generation
- [x] Add URL deduplication
- [x] Add discovery tests

### Phase 3 — Public Web Fetcher
- [x] HTTP/HTTPS fetching
- [x] Redirect handling
- [x] Timeout handling
- [x] HTTP error handling
- [x] HTML content validation
- [x] robots.txt checking
- [x] Custom user-agent
- [x] Add fetcher tests

### Phase 4 — Parser
- [x] JSON-LD / Schema.org extraction
- [x] Meta description extraction
- [x] OpenGraph/title fallback
- [x] Phone extraction
- [x] Email extraction
- [x] Address extraction
- [x] Category extraction
- [x] Add parser tests

### Phase 5 — Normalization & Deduplication
- [x] Normalize text
- [x] Normalize names
- [x] Normalize phone numbers
- [x] Normalize email addresses
- [x] Normalize URLs
- [x] Generate lead identity keys
- [x] Deduplicate leads
- [x] Merge duplicate records
- [x] Preserve source URLs
- [x] Complete dedicated normalizer pytest coverage

### Phase 6 — Engine Integration
- [x] Connect discovery to fetcher
- [x] Connect fetcher to parser
- [x] Connect parser to normalizer
- [x] Create ScrapeResult
- [x] Track fetch failures
- [x] Track parse failures
- [x] Add engine tests

### Phase 7 — Real Web Discovery
- [x] Implement real public-web discovery provider
- [x] Keep discovery provider-based and replaceable
- [x] Support multiple discovery providers
- [x] Avoid brittle direct search-engine HTML scraping where possible
- [x] Respect public-web access rules

### Phase 8 — Relevance Filtering
- [x] Keyword relevance scoring
- [x] Location relevance scoring
- [x] Category relevance filtering
- [x] Requirements matching
- [x] Remove irrelevant candidates

### Phase 9 — Result Quality
- [x] Improve phone extraction
- [x] Improve address extraction
- [x] Improve location extraction
- [x] Improve business/category extraction
- [x] Distinguish business website from source URL
- [x] Add lead quality checks

### Phase 10 — Rate Limiting & Crawl Policy
- [x] Implement crawl-delay handling
- [x] Add request throttling
- [x] Add per-domain limits
- [x] Add retry policy
- [x] Improve robots.txt failure handling

### Phase 11 — CLI
- [x] Add keyword argument
- [x] Add location argument
- [x] Add optional requirements argument
- [x] Add result limit argument
- [x] Validate CLI input

### Phase 12 — Terminal Output
- [x] Print result count
- [x] Print structured lead records
- [x] Print source information
- [x] Print fetch/parse summary
- [x] Keep terminal output readable
- [x] Optional JSON/CSV output

### Phase 13 — Live Web Smoke Test
- [ ] Run real doctor + Shahjahanpur search
- [ ] Verify discovery
- [ ] Verify fetching
- [ ] Verify parsing
- [ ] Verify normalization
- [ ] Verify deduplication
- [ ] Verify terminal output

### Phase 14 — Robustness
- [ ] Handle 404 responses
- [ ] Handle 403 responses
- [ ] Handle 429 responses
- [ ] Handle 500 responses
- [ ] Handle timeouts
- [ ] Handle redirects
- [ ] Handle empty HTML
- [ ] Handle malformed HTML
- [ ] Handle invalid JSON-LD
- [ ] Handle non-HTML pages
- [ ] Handle duplicate URLs
- [ ] Handle duplicate leads
- [ ] Handle dead domains
- [ ] Handle robots-blocked pages
- [ ] Ensure engine does not crash on individual failures

### Phase 15 — Documentation
- [ ] Write README
- [ ] Document installation
- [ ] Document quick start
- [ ] Document CLI usage
- [ ] Document architecture
- [ ] Document discovery providers
- [ ] Document Lead schema
- [ ] Document public-web rules
- [ ] Document robots policy
- [ ] Add examples
- [ ] Document limitations

### Phase 16 — Packaging
- [ ] Create/update pyproject.toml
- [ ] Add package metadata
- [ ] Add CLI entry point if appropriate
- [ ] Verify package installation

### Phase 17 — Final Test & Release Audit
- [ ] Run full pytest suite
- [ ] Run Python compile checks
- [ ] Run CLI smoke test
- [ ] Run live-web smoke test
- [ ] Run git diff --check
- [ ] Review documentation
- [ ] Review scope boundaries
- [ ] Commit final V1
- [ ] Push final V1

## Current Status

Foundation             [x]
Data Model             [x]
Discovery abstraction  [x]
Discovery tests        [x]
Fetcher                [x]
Fetcher tests          [x]
Parser                 [x]
Parser tests           [x]
Engine                 [x]
Engine tests           [x]
Pytest configuration   [x]
Normalizer tests       [x]
Real discovery         [x]
Relevance              [x]
CLI                    [ ]
Live smoke test        [ ]
Hardening              [ ]
Documentation          [ ]
Packaging              [ ]
Final release          [ ]
