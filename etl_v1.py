from datetime import datetime, timezone
import logging
import sys

import pandas as pd
import requests

from extract import CITIES, DB_PATH, LOG_DIR ,fetch_city, save_raw  
import sqlite3
logger = logging.getLogger(__name__)


def flatten(payload: dict, city_name: str) -> pd.DataFrame:
    """One API response -> table with one row per hour."""
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city_name
    df["latitude"] = payload["latitude"]
    df["longitude"] = payload["longitude"]
    return df


def extract() -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch every city. Return (good results, names of cities that failed)."""
    raw, failed = [], []
    for city in CITIES:
        try:
            payload = fetch_city(city)
            save_raw(city["name"], payload)
            raw.append((city["name"], payload))
            logger.info("Extracted %s", city["name"])
        except requests.RequestException as err:
            logger.error("%s: giving up: %s", city["name"], err)
            failed.append(city["name"])
    return raw, failed


RENAME = {
    "time": "observed_at_utc",
    "temperature_2m": "temperature_c",
    "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}

COLUMNS = [
    "city", "observed_at_utc", "observed_at_local", "temperature_c", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "weather_code", "ingested_at_utc",
]


def transform(raw):
    """Flatten, clean and standardise."""
    df = pd.concat([flatten(payload, city) for city, payload in raw], ignore_index=True)

    df = df.rename(columns=RENAME)                                          # 1. new names
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True) # 2. text -> UTC datetime
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert("Europe/London")  # 3. London time
    df = df.drop_duplicates(subset=["city", "observed_at_utc"], keep="last")        # 4. no duplicates
    df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return df[COLUMNS]

def load(df: pd.DataFrame, db_path: db_path=DB_PATH) -> int:
    """Write to SQLite. Return number of rows written."""
    out = df.copy()
    out["observed_at_utc"] = out["observed_at_utc"].map(pd.Timestamp.isoformat)   # datetime -> text
    out["observed_at_local"] = out["observed_at_local"].map(pd.Timestamp.isoformat)   # datetime -> text
    out = out.astype(object).where(out.notna(), None)                          # missing -> NULL
    rows = list(out.itertuples(index=False, name=None))

    conn = sqlite3.connect(db_path)
    with conn:                          # saves (commits) if no error
        conn.execute(CREATE_TABLE)
        conn.executemany(INSERT, rows)
    conn.close()
    return len(rows)
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS weather_hourly (
    city              TEXT    NOT NULL,
    observed_at_utc   TEXT    NOT NULL,
    observed_at_local TEXT    NOT NULL,
    temperature_c     REAL,
    feels_like_c      REAL,
    humidity_pct      INTEGER,
    precipitation_mm  REAL,
    wind_speed_kmh    REAL,
    weather_code      INTEGER,
    ingested_at_utc   TEXT    NOT NULL,
    PRIMARY KEY (city, observed_at_utc)
);
"""

INSERT = """
INSERT OR REPLACE INTO weather_hourly
    (city, observed_at_utc, observed_at_local, temperature_c, feels_like_c, humidity_pct,
     precipitation_mm, wind_speed_kmh, weather_code, ingested_at_utc)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""
def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        ],
    )


def main():
    setup_logging()
    logger.info("Pipeline started")
    raw, failed = extract()
    if raw:                                   # load the cities that worked
        rows = load(transform(raw))
        logger.info("Loaded %d rows", rows)
    if failed:                                # then fail loudly
        logger.error("Run FAILED: no data for %s", ", ".join(failed))
        sys.exit(1)
    logger.info("Run succeeded")


if __name__ == "__main__":
    main()