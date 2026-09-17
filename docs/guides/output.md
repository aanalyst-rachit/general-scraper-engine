# Output Formats

## Terminal

The default terminal output contains lead count, lead fields, source information, and discovery/fetch/parse summary.

## JSON

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --json results.json
```

The JSON file contains an array of serialized `Lead` records.

Direct-source adapters can also write their normalized leads to JSON:

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5 \
  --json google-maps-results.json
```

## CSV

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --csv results.csv
```

Nested fields such as social profiles and raw/extra data are serialized as JSON strings inside the CSV.

Direct-source adapters can also write normalized leads to CSV:

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5 \
  --csv google-maps-results.csv
```

## DuckDB

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --save-db \
  --db-path data/my-leads.duckdb
```

The repository normalizes leads and uses identity keys to avoid duplicate records.

Direct-source results can also be persisted to DuckDB:

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5 \
  --save-db \
  --db-path data/google-maps.duckdb
```
