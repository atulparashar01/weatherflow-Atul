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
4. Install the dependencies and the package itself:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install -e .
   ```
   To also use the notebooks and run tests, install `requirements-dev.txt` instead of `requirements.txt`.
5. Add your WeatherAPI key. Sign up (free) at weatherapi.com, then copy the example file and put your key in it:
   ```bash
   cp .env.example .env
   # open .env and replace your_key_here with your real key
   ```
   `.env` is ignored by Git. Never commit it, and never put the key in `config.yaml` or the README.

## How to run the pipeline

With your virtual environment active, from the repo root:

```bash
python -m weatherflow run                      # both sources (default)
python -m weatherflow run --source open_meteo  # Open-Meteo only
python -m weatherflow run --source weatherapi  # WeatherAPI only
```

If `WEATHERAPI_KEY` is missing and WeatherAPI is requested, the run stops straight away with a clear message and exit code 1. No request is sent.

The pipeline has five steps:
1. **Extract:** calls the Open-Meteo and WeatherAPI APIs for each city (retrying timeouts and server errors up to 3 times, never retrying 401 or 403) and saves the raw JSON in `data/raw/`.
2. **Transform:** cleans the data into one table: UTC and London times, units, weather descriptions, Beaufort wind scale and an outdoor work risk level.
3. **Validate:** runs 8 data quality checks. Bad rows are quarantined, serious problems stop the run, and a report is written to `docs/dq_reports/`.
4. **Load:** writes the good rows into a star schema in `data/weather.db` (SQLite) inside one transaction.
5. **Save:** writes the same rows as Parquet files in `data/processed/`, partitioned by run date.

Example output:

```
2026-11-18 18:19:03 | INFO | weatherflow.pipeline | Pipeline started
2026-11-18 18:19:03 | INFO | weatherflow.extract  | London: 48 hourly records saved to ...
...
2026-11-18 18:19:03 | INFO | weatherflow.transform | Transformed 240 rows for 5 cities
2026-11-18 18:19:03 | INFO | weatherflow.validate | Validation: 240 good rows, 0 quarantined rows
2026-11-18 18:19:03 | INFO | weatherflow.validate | DQ report written to ...
2026-11-18 18:19:03 | INFO | weatherflow.load     | Loaded 240 rows into fact_weather_hourly
2026-11-18 18:19:04 | INFO | weatherflow.pipeline | Run succeeded
```

The command exits with code 1 if a city could not be fetched or a blocking data quality check failed.

## Configuration
All settings are in `config.yaml`: the API, the cities, the folders, the `dim_date` range and the data quality thresholds. Change a limit there, not in the code.

## Data model
The database is a star schema (see `docs/erd.md`):

- `fact_weather_hourly`: one row per city, per hour, per source. Primary key `(city_id, observed_at_utc, source)`.
- `dim_city`: one row per city.
- `dim_date`: one row per calendar day (the London date), with weekday and weekend flags.

Running the pipeline twice gives the same row counts. The load is an upsert (`INSERT ... ON CONFLICT DO UPDATE`), so existing hours are updated, not duplicated. The whole load runs in one transaction, so a failure saves nothing.

Times are stored in UTC (`observed_at_utc`). The London date is used for `date_id`, because the business plans by UK calendar day.

## Data quality
Validation runs between transform and load (`src/weatherflow/validate.py`):

| Severity | What happens | Checks |
|---|---|---|
| Quarantine | The row is set aside with a reason in `data/quarantine/` | required fields not empty, temperature range, humidity range, rain and wind not negative |
| Fail run | Nothing is loaded and the run exits with code 1 | no duplicate rows, every city has every hour |
| Warn | A warning is logged and the data still loads | data freshness, feels-like close to temperature, the two sources agree on temperature (threshold `cross_source_temp_gap_c` in `config.yaml`) |

Every run writes a summary to `docs/dq_reports/<timestamp>.md`.

To see the checks work on purpose, run:

```bash
python scripts/inject_bad_data.py
```

It injects a 99 °C reading (quarantined) and a duplicate row (the run is stopped).

## Check the data with SQL

```bash
sqlite3 data/weather.db < sql/analysis_queries.sql
```

No `sqlite3` command on your computer? Use Python instead:

```bash
python -c "import sqlite3; print(sqlite3.connect('data/weather.db').execute('SELECT c.city_name, COUNT(*) FROM fact_weather_hourly f JOIN dim_city c ON c.city_id = f.city_id GROUP BY c.city_name').fetchall())"
```

## Tests

Install the package and the dev tools first (`python -m pip install -r requirements-dev.txt` and `python -m pip install -e .`), then run:

```bash
python -m pytest -v --cov=src --cov-report=term-missing
```

The tests never call the real API. They use a saved response (`tests/fixtures/open_meteo_london.json`) and a mocked API, so they run offline.

| File | What it tests |
|---|---|
| `tests/test_transform.py` | flatten, Fahrenheit, unknown weather code, deduplicate, `outdoor_work_risk` rules and boundaries |
| `tests/test_validate.py` | clean data passes, a 99 °C row is quarantined, a duplicate raises `DataQualityError`, quarantine file and DQ report are written |
| `tests/test_extract.py` | retry on a 503, no retry on a 404, raw file written (API mocked) |
| `tests/test_load.py` | loading the same data twice keeps the same row count (idempotency) |
| `tests/test_main.py` | `main(["run"])` returns 0 or 1, backfill dates are passed on (pipeline mocked) |
| `tests/test_config.py` | paths made absolute, a missing section or key is reported by name |
| `tests/test_watermark.py` | high-water mark ignores future forecast hours, is empty on a new database |

Latest result: 36 passed. Coverage summary (every module in `src/weatherflow/` is included):

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
src\weatherflow\__init__.py        0      0   100%
src\weatherflow\__main__.py       24      2    92%
src\weatherflow\config.py         19      1    95%
src\weatherflow\extract.py        55     20    64%
src\weatherflow\load.py           62      6    90%
src\weatherflow\pipeline.py       96     76    21%
src\weatherflow\reference.py       6      0   100%
src\weatherflow\transform.py      53      0   100%
src\weatherflow\validate.py      105     13    88%
------------------------------------------------------------
TOTAL                            420    118    72%
```

`pipeline.py` is the weakest module (21%). It joins the other steps together and is checked by running the real pipeline, not by unit tests.

## Project structure
```
weatherflow-Atul/
├── config.yaml                  # all settings and thresholds
├── .env.example                 # variables you need, with fake values (copy to .env)
├── pyproject.toml               # package definition
├── requirements.txt             # packages the pipeline needs
├── requirements-dev.txt         # extra tools for notebooks and tests
├── src/weatherflow/
│   ├── __init__.py              # empty, makes this a package
│   ├── __main__.py              # command line: python -m weatherflow run
│   ├── pipeline.py              # extract -> transform -> validate -> load
│   ├── config.py                # reads config.yaml
│   ├── extract.py               # calls the API (with retries)
│   ├── transform.py             # cleans the data and adds derived columns
│   ├── validate.py              # data quality checks and quarantine
│   ├── load.py                  # star schema load and Parquet output
│   ├── reference.py             # loads the weather code lookup
│   └── reference/               # wmo_codes.csv and weatherapi_codes.csv (weather code lookups)
├── sql/
│   ├── schema.sql               # the three tables
│   └── analysis_queries.sql     # 5 analysis queries (joins on the star schema)
├── scripts/
│   ├── compare_formats.py       # CSV vs Parquet file size
│   ├── inject_bad_data.py       # proves the quality gate works
│   ├── force_error.py           # proves a failed load saves nothing
│   └── show_counts.py           # prints the row count of each table
├── tests/
│   ├── conftest.py              # shared fixtures
│   ├── fixtures/                # saved API response used by the tests
│   ├── test_transform.py
│   ├── test_validate.py
│   ├── test_extract.py
│   ├── test_load.py
│   ├── test_main.py
│   ├── test_config.py
│   ├── test_watermark.py
│   ├── test_normalise_weatherapi.py
│   ├── test_extract_weatherapi.py
│   └── test_cross_source.py
├── notebooks/                   # 01_explore.ipynb
├── docs/                        # data dictionary, ERD, reports, reflections, adr/ (decisions)
└── etl_v1.py                    # Week 1 version, kept for history
```
`data/` and `*.db` are created when you run the pipeline. They are not stored in Git.

## Author
Atul
