"""Transform step: turn the raw API responses into one clean table.

Every function takes a DataFrame and returns a new DataFrame. None of them
read files, call the API or write to the database.
"""
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

RENAME = {
    "time": "observed_at_utc",
    "temperature_2m": "temperature_c",
    "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}


COLUMNS = [
    "city", "observed_at_utc", "observed_at_local", "temperature_c", "feels_like_c",
    "humidity_pct", "precipitation_mm", "wind_speed_kmh", "weather_code",
    "weather_description", "weather_category", "ingested_at_utc",
]

def flatten_payload(payload: dict, city: str) -> pd.DataFrame:
    """Turn one API response into a table with one row per hour."""
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city
    return df


def standardise_columns(df: pd.DataFrame, local_timezone: str = "Europe/London") -> pd.DataFrame:
    """Rename columns, parse the time as UTC and add the local time."""
    df = df.rename(columns=RENAME)
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert(local_timezone)
    return df


def add_weather_description(df: pd.DataFrame, wmo_codes: pd.DataFrame) -> pd.DataFrame:
    """Join the WMO lookup table. Unknown or missing codes become "unknown"."""
    df = df.merge(wmo_codes, on="weather_code", how="left", validate="many_to_one")
    df["weather_description"] = df["weather_description"].fillna("unknown")
    df["weather_category"] = df["weather_category"].fillna("unknown")
    return df


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add temperature_f, wind_speed_ms, beaufort_scale and outdoor_work_risk. (Step 5)"""
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per city and hour (the last one if there are repeats)."""
    return df.drop_duplicates(subset=["city", "observed_at_utc"], keep="last")


def transform(raw_records: list[tuple[str, dict]], wmo_codes: pd.DataFrame) -> pd.DataFrame:
    """Run every transformation in order and return the clean table."""
    frames = [flatten_payload(payload, city) for city, payload in raw_records]
    df = pd.concat(frames, ignore_index=True)

    df = standardise_columns(df)
    df = add_weather_description(df, wmo_codes)
    df = add_derived_metrics(df)
    df = deduplicate(df)
    df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    logger.info("Transformed %d rows for %d cities", len(df), df["city"].nunique())
    return df[COLUMNS]