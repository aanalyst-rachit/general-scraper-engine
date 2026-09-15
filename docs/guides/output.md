# Output Formats

## Terminal

The default terminal output contains lead count, lead fields, source information, and discovery/fetch/parse summary.

## JSON

```bash
python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --json results.json
```

The JSON file contains an array of serialized `Lead` records.

## CSV

```bash
python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --csv results.csv
```

Nested fields such as social profiles and raw/extra data are serialized as JSON strings inside the CSV.

## DuckDB

```bash
python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --save-db \\
  --db-path data/my-leads.duckdb
```

The repository normalizes leads and uses identity keys to avoid duplicate records.
