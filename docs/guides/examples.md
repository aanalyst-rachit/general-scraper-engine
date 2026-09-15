# Examples

## Doctors in a City

```bash
python run_scraper.py \\
  --keyword doctor \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --limit 25
```

## Restaurants with JSON

```bash
python run_scraper.py \\
  --keyword restaurant \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --limit 25 \\
  --json restaurants.json
```

## Business Leads with CSV

```bash
python run_scraper.py \\
  --keyword "real estate agent" \\
  --location "Lucknow, Uttar Pradesh" \\
  --csv leads.csv
```

## Persistent Lead Collection

```bash
python run_scraper.py \\
  --keyword dentist \\
  --location "Shahjahanpur, Uttar Pradesh" \\
  --save-db \\
  --db-path data/dentists.duckdb
```
