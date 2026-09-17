# Testing

Run the complete test suite:

```bash
python -m pytest -q
```

The test suite covers discovery, providers, fetching, browser acquisition, parsing, normalization, relevance, quality validation, engine behavior, CLI behavior, source adapters, and DuckDB persistence.

## CLI Tests

CLI-specific tests can be run with:

```bash
python -m pytest tests/test_cli.py -q
```

The CLI tests cover argument parsing, output formats, persistence, source selection, and direct-source execution paths.

## Browser Source Tests

Google Maps browser adapter tests can be run with:

```bash
python -m pytest tests/test_source_google_maps_browser.py -q
```

Browser tests use mocked or controlled browser fixtures for deterministic automated testing. Real browser acquisition can also be exercised manually through the CLI.

## Python Compilation

Python compilation can also be checked with:

```bash
python -m compileall scraper run_scraper.py
```
