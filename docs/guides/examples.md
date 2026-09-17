# Examples

## Doctors in a City

```bash
python run_scraper.py \
  --keyword doctor \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 25
```

## Restaurants with JSON

```bash
python run_scraper.py \
  --keyword restaurant \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 25 \
  --json restaurants.json
```

## Business Leads with CSV

```bash
python run_scraper.py \
  --keyword "real estate agent" \
  --location "Lucknow, Uttar Pradesh" \
  --csv leads.csv
```

## Persistent Lead Collection

```bash
python run_scraper.py \
  --keyword dentist \
  --location "Shahjahanpur, Uttar Pradesh" \
  --save-db \
  --db-path data/dentists.duckdb
```

## Google Maps Browser

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

## Google Maps Places API

```bash
export GOOGLE_MAPS_API_KEY="your-api-key"

python run_scraper.py \
  --source google-maps \
  --google-maps-api-key "$GOOGLE_MAPS_API_KEY" \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

## Justdial Browser

```bash
python run_scraper.py \
  --source justdial-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --limit 5
```

## Category Filter

Direct-source results can be filtered by exact normalized Lead category.

```bash
python run_scraper.py \
  --source google-maps-browser \
  --keyword "restaurant" \
  --location "Shahjahanpur, Uttar Pradesh" \
  --category "Chinese restaurant" \
  --limit 5
```
