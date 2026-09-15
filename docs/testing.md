# Testing

Run the complete test suite:

```bash
python -m pytest -q
```

The test suite covers discovery, providers, fetching, parsing, normalization, relevance, quality validation, engine behavior, CLI behavior and DuckDB persistence.

## Python Compilation

Python compilation can also be checked with:

```bash
python -m compileall scraper run_scraper.py
```
