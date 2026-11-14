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
   To also use the notebooks and run tests, install `requirements-dev.txt` instead.

## How to run the pipeline

With your virtual environment active, from the repo root:

```bash
python etl_v1.py
```

This runs three steps:
1. **Extract:** calls the Open-Meteo API for each city (retrying temporary errors up to 3 times) and saves the raw JSON in `data/raw/`.
2. **Transform:** cleans the data into one table (UTC datetime, column names with units, no duplicates).
3. **Load:** writes the rows into the `weather_hourly` table in `weather.db`.

Example output (also saved in `logs/pipeline.log`):

```
2026-11-14 12:29:33,118 INFO    __main__: Pipeline started
2026-11-14 12:29:33,311 INFO    __main__: Extracted London
2026-11-14 12:29:33,498 INFO    __main__: Extracted Manchester
2026-11-14 12:29:33,652 INFO    __main__: Extracted Birmingham
2026-11-14 12:29:33,804 INFO    __main__: Extracted Edinburgh
2026-11-14 12:29:33,949 INFO    __main__: Extracted Cardiff
2026-11-14 12:29:34,210 INFO    __main__: Loaded 240 rows
2026-11-14 12:29:34,211 INFO    __main__: Run succeeded
```

If a city still fails after the retries, the other cities are loaded, the log shows `Run FAILED: no data for <city>`, and the script exits with code 1.

Times are stored in UTC (`observed_at_utc`), with a London-time column (`observed_at_local`) for reading.

Running it twice gives the same row count. The table has a primary key on `(city, observed_at_utc)` and the load uses `INSERT OR REPLACE`, so existing hours are replaced, not duplicated.

Check the data with SQL:

```bash
sqlite3 weather.db < sql/week1_queries.sql
```

No `sqlite3` command on your computer? Use Python instead:

```bash
python -c "import sqlite3; print(sqlite3.connect('weather.db').execute('SELECT city, COUNT(*) FROM weather_hourly GROUP BY city').fetchall())"
```

## Project structure
```
weatherflow-Atul/
├── extract.py              # calls the API and saves raw JSON
├── etl_v1.py               # Extract -> Transform -> Load into SQLite
├── requirements.txt        # packages the pipeline needs
├── requirements-dev.txt    # extra tools for notebooks and tests
├── sql/week1_queries.sql   # example queries
├── notebooks/              # 01_explore.ipynb
└── docs/                   # data dictionary, architecture, critique, reflections
```
`data/`, `logs/` and `weather.db` are created when you run the pipeline. They are not stored in Git.

## Author
Atul
