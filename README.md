# WeatherFlow

## Goal
A regional events company plans outdoor work in five UK cities: London, Manchester, Birmingham, Edinburgh and Cardiff. They need hourly weather they can trust, refreshed automatically, with a dashboard that flags risky conditions. WeatherFlow is the data pipeline that delivers this.

## How to set up
1. Install Python 3.11+ and Git.
2. Clone the repo:
   ```bash
   git clone https://github.com/atulparashar01/weatherflow-Atul.git
   cd weatherflow-Atul
   ```
3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:    .venv\Scripts\activate
   # Mac/Linux:  source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   ## How to run the pipeline

With your virtual environment active, from the repo root:

```bash
python etl_v1.py
```

This runs three steps:
1. **Extract:** calls the Open-Meteo API for each city and saves the raw JSON in `data/raw/`.
2. **Transform:** cleans the data into one table (datetime, column names with units, no duplicates).
3. **Load:** writes the rows into the `weather_hourly` table in `weather.db`.

Example output:

```
extracted London
extracted Manchester
extracted Birmingham
extracted Edinburgh
extracted Cardiff
Loaded 240 rows
```

Running it twice gives the same row count. The table has a primary key on `(city, observed_at)` and the load uses `INSERT OR REPLACE`, so existing hours are replaced, not duplicated.

Check the data with SQL:

```bash
sqlite3 weather.db < sql/week1_queries.sql
```

## Author
Atul