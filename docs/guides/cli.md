# CLI Usage

Show all available options:

```bash
python run_scraper.py --help
```

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| `--keyword` | Yes | — | Search keyword |
| `--location` | No | empty | Target location |
| `--requirements` | No | empty | Additional requirements |
| `--limit` | No | `50` | Maximum discovered pages to process |
| `--provider` | No | `brave` | `brave` or `searxng` |
| `--searxng-url` | No | `http://127.0.0.1:8080` | SearXNG base URL |
| `--json` | No | — | Write leads to JSON |
| `--csv` | No | — | Write leads to CSV |
| `--save-db` | No | disabled | Persist leads to DuckDB |
| `--db-path` | No | `data/leads.duckdb` | DuckDB database path |

The keyword must not be empty and the limit must be a positive integer.
