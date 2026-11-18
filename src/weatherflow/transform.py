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
    "is_day": "is_daylight",
}

# Beaufort scale: lower limit of each force (0 to 12) in metres per second
BEAUFORT_LIMITS_MS = [0, 0.5, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7]

COLUMNS = [
    "city", "observed_at_utc", "observed_at_local", "temperature_c", "temperature_f",
    "feels_like_c", "humidity_pct", "precipitation_mm", "wind_speed_kmh", "wind_speed_ms",
    "beaufort_scale", "weather_code", "weather_description", "weather_category",
    "is_daylight", "outdoor_work_risk", "ingested_at_utc",
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
    df["is_daylight"] = df["is_daylight"].astype("boolean")    # 1 -> True, 0 -> False
    return df


def add_weather_description(df: pd.DataFrame, wmo_codes: pd.DataFrame) -> pd.DataFrame:
    """Join the WMO lookup table. Unknown or missing codes become "unknown"."""
    df = df.merge(wmo_codes, on="weather_code", how="left", validate="many_to_one")
    df["weather_description"] = df["weather_description"].fillna("unknown")
    df["weather_category"] = df["weather_category"].fillna("unknown")
    return df


def calculate_beaufort(wind_speed_ms: pd.Series) -> pd.Series:
    """Convert wind speed in m/s to the Beaufort scale (0 to 12)."""
    bins = BEAUFORT_LIMITS_MS + [float("inf")]
    force = pd.cut(wind_speed_ms, bins=bins, labels=range(13), right=False)
    return force.astype("Int64")


def classify_outdoor_risk(df: pd.DataFrame) -> pd.Series:
    """Return "high", "medium" or "low" for each row using the outdoor work rules."""
    high = (
        (df["beaufort_scale"] >= 7)
        | df["weather_category"].isin(["storm", "snow"])
        | (df["precipitation_mm"] >= 4)
    ).fillna(False)
    medium = (
        (df["beaufort_scale"] >= 5)
        | (df["precipitation_mm"] >= 1)
        | (df["temperature_c"] <= 0)
    ).fillna(False)

    risk = pd.Series("low", index=df.index)
    risk[medium] = "medium"
    risk[high] = "high"                      # high is applied last, so it wins
    return risk


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add temperature_f, wind_speed_ms, beaufort_scale and outdoor_work_risk."""
    df = df.copy()
    df["temperature_f"] = df["temperature_c"] * 9 / 5 + 32
    df["wind_speed_ms"] = df["wind_speed_kmh"] / 3.6
    df["beaufort_scale"] = calculate_beaufort(df["wind_speed_ms"])
    df["outdoor_work_risk"] = classify_outdoor_risk(df)
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