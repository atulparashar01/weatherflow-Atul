# ADR 001: Add WeatherAPI as a second source

**Status:** Accepted
**Date:** 22 November 2026
**Task:** 3.1 A Second Source and Secrets

## Context

The client does not want to rely on one weather provider. Open-Meteo needs no key. WeatherAPI.com does, and a key is a secret: anyone who has it can use my quota. Two sources also means two opinions about the same hour, so the pipeline must notice when they disagree.

## Decisions

### 1. The key lives in `.env`, never in Git, config or logs
- `WEATHERAPI_KEY` is read from `.env` with `python-dotenv`. `.env` is in `.gitignore`.
- `.env.example` is committed with a fake value, so a new person knows which variables to set.
- If the key is missing the run stops at once with exit code 1, before any request is sent.
- The key is part of the request URL, so error messages and `response.url` can contain it. Logs show only the city, the error type and the status code (`_describe()` in `extract.py`). A unit test checks the key never appears in the logs.
- Checked on 22 Nov 2026: the first 6 characters of the key are not in `git log -p`, nor in `data/`, `docs/`, `src/`, `tests/`, `config.yaml`, `README.md` or `.env.example`.

### 2. Time: use `time_epoch`, not `time`
The WeatherAPI docs do not say which timezone `time` uses. I tested it for New York (one hour of one response):

| Field | Value |
|---|---|
| `location.tz_id` | America/New_York |
| `time` (text) | 2026-11-22 12:00 |
| `time_epoch` as UTC | 2026-11-22 17:00 UTC |
| `time_epoch` as America/New_York | 2026-11-22 12:00 |

So `time` is **local time at the location** and `time_epoch` is a true UTC moment. For London in November the two look the same, because London is on UTC+0, so London alone would have proved nothing. The pipeline uses `time_epoch` (`pd.to_datetime(..., unit="s", utc=True)`).

### 3. One pipeline, two small adapters
Each source has one small, pure function that gives my standard columns (`flatten_payload` + `standardise_columns` for Open-Meteo, `normalise_weatherapi` for WeatherAPI). After that, the same derive, validate and load code runs. Sources are told apart by the `source` column, which is part of the primary key: `open_meteo_forecast`, `open_meteo_archive`, `weatherapi_forecast`.

### 4. Weather codes: a reference CSV
WeatherAPI uses its own condition codes (for example 1000), not WMO codes. `weatherapi_codes.csv` maps its 60 codes to my 7 categories. Judgement calls: sleet and freezing rain are `rain`; ice pellets and blowing snow are `snow`; haze, smoke, smog, dust and mist are `fog` (there is no visibility category); anything with thunder is `storm`.

### 5. No backfill for WeatherAPI
The free plan gives only the past day of history and a 3-day forecast. WeatherAPI rows are therefore **incremental only**: each run loads today's 24 hours. The 30-day backfill stays Open-Meteo only (`open_meteo_archive`).

### 6. Cross-source check (warn)
For the same city and hour, the pipeline compares `temperature_c` from the two sources and warns if they differ by more than `cross_source_temp_gap_c` in `config.yaml` (3 °C to start). The DQ report shows the count and the worst city. It is a warning, not a failure: a disagreement does not stop the run, and both values are kept.

### 7. When the sources disagree by 5 °C, which one does the dashboard show?

**Decision: the dashboard shows Open-Meteo, and marks that hour "sources disagree".** *(This is my reasoning for the "check your understanding" question. Edit it if you decide differently.)*

Why:
- Neither source is the truth. Both are forecasts or model data, so a 5 °C gap tells me one of them is wrong but not which.
- Open-Meteo is the primary source: it has the longer, continuous history (backfill, 48 hours per run), it needs no key, and I know its behaviour best.
- Silently picking one would hide a problem. Marking the hour keeps the user informed, and both rows stay in `fact_weather_hourly`, so nothing is lost.
- The marker matters for the business: a 5 °C difference can change an outdoor-work risk level.

Alternatives I rejected: showing the average (it can be wrong for both sources), or always showing the newest source (it changes with run order, not with quality).

## Consequences
- WeatherAPI adds 120 rows per run (24 hours × 5 cities), about 3,600 calls a month, well under the 100,000 free limit.
- The `source` column must be filtered in every dashboard query, or rows are counted twice.
- The cross-source check only compares hours that are in both sources, so it says nothing about past days that only Open-Meteo has.
