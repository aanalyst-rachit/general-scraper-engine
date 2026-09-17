<div class="gse-hero">

# General Scraper Engine

<div class="tagline">

A modular, policy-aware Python engine for discovering, acquiring, extracting, validating, and storing structured leads from the public web.

</div>

<div class="gse-actions">

<a class="gse-button primary" href="getting-started/installation/">Get Started</a>
<a class="gse-button secondary" href="https://github.com/aanalyst-rachit/general-scraper-engine">View on GitHub</a>

</div>

</div>

---

<div class="gse-grid">

<div class="gse-card">

### Python Package

Install directly with pip and integrate the engine into your Python workflows.

</div>

<div class="gse-card">

### Current Release

Version **1.0.3** with release notes available in the documentation.

</div>

<div class="gse-card">

### Public Web

Built around public-web acquisition and explicit access boundaries.

</div>

</div>

---

<div class="gse-grid">

<div class="gse-card">

<div class="icon">01</div>

### Discovery

Find relevant pages using pluggable discovery providers such as Brave Search and SearXNG.

</div>

<div class="gse-card">

<div class="icon">02</div>

### HTTP-first acquisition

Use inexpensive HTTP fetching by default, with browser and external-provider fallback when required.

</div>

<div class="gse-card">

<div class="icon">03</div>

### Structured extraction

Extract leads from JSON-LD, Schema.org, metadata, contact information, and visible page content.

</div>

<div class="gse-card">

<div class="icon">04</div>

### Policy-aware

Respect public-web boundaries, robots.txt rules, crawl delays, request limits, and access restrictions.

</div>

<div class="gse-card">

<div class="icon">05</div>

### Quality and deduplication

Validate, normalize, merge, and deduplicate extracted leads before output.

</div>

<div class="gse-card">

<div class="icon">06</div>

### Multiple outputs

Write results to terminal, JSON, CSV, or DuckDB with optional run-level metrics.

</div>

</div>

---

## Pipeline

The engine separates discovery, acquisition, extraction, validation, and persistence into independent stages.

<div class="gse-pipeline">

```text
Discovery
    |
    v
Relevance
    |
    v
Policy
    |
    v
Acquisition
    |
    v
Content Quality
    |
    v
Parse / Extract
    |
    v
Location / Lead Quality
    |
    v
Normalize / Deduplicate
    |
    v
Persistence / Output
```

</div>

HTTP remains the cheapest default acquisition method. Browser and external-provider strategies are introduced only when content or workload requires them.

---

## Quick Start

Install the package:

```bash
pip install general-scraper-engine
```

Then run a basic scrape:

```bash
general-scraper-engine \
  --keyword "dentist" \
  --location "New York" \
  --output leads.json
```

See the complete setup in the **[Quick Start](getting-started/quickstart.md)** guide.

---

## What it supports

| Area | Capabilities |
|---|---|
| Discovery | Brave Search, SearXNG, provider protocol, caching |
| Acquisition | HTTP, Playwright browser, external providers, Google Maps, Justdial |
| Crawling | Same-site crawling, depth/page limits, domain controls |
| Extraction | JSON-LD, Schema.org, metadata, contacts, addresses |
| Relevance | Keyword, location, category, requirements |
| Quality | Content quality, lead quality, location validation |
| Data processing | Normalization, deduplication, merging |
| Persistence | Terminal, JSON, CSV, DuckDB |
| Reliability | Retries, throttling, bounded concurrency, caching |

---

## Documentation

<div class="gse-grid">

<div class="gse-card">

### Getting Started

Install the engine and run your first scrape.

[Installation](getting-started/installation.md)

[Quick Start](getting-started/quickstart.md)

</div>

<div class="gse-card">

### Guides

Learn CLI usage, output formats, providers, crawling examples, and public-web policy.

[Explore Guides](guides/cli.md)

</div>

<div class="gse-card">

### Reference

Understand the architecture, lead schema, programmatic API, and error model.

[Open Reference](reference/architecture.md)

</div>

</div>

---

## Public-Web Boundary

General Scraper Engine is designed for public-web acquisition.

It does **not** provide:

- Login bypass
- CAPTCHA bypass
- Private-page access
- Authentication bypass
- Access-control circumvention

Robots.txt and crawl-policy controls are part of the acquisition boundary.

See **[Public-Web and Robots Policy](guides/policy.md)** for details.

---

## Project

- [Testing](testing.md)
- [Limitations](limitations.md)
- [Contributing](contributing.md)
- [v1.0.3 Release Notes](release/v_1.0.3/RELEASE_NOTES.md)

---

<div align="center">

**General Scraper Engine**

Modular - Policy-aware - HTTP-first - Extensible

</div>