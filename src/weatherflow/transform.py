"""Transform step: turn the raw API responses into one clean table."""
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
    "humidity_pct", "precipitation_mm", "wind_speed_kmh", "weather_code", "ingested_at_utc",
]


def flatten(payload: dict, city_name: str) -> pd.DataFrame:
    """Turn one API response into a table with one row per hour."""
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city_name
    return df


def transform(raw: list[tuple[str, dict]], local_timezone: str = "Europe/London") -> pd.DataFrame:
    """Flatten every city, store times in UTC, add local time and remove duplicates."""
    df = pd.concat([flatten(payload, city) for city, payload in raw], ignore_index=True)

    df = df.rename(columns=RENAME)
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert(local_timezone)
    df = df.drop_duplicates(subset=["city", "observed_at_utc"], keep="last")
    df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    logger.info("Transformed %d rows for %d cities", len(df), df["city"].nunique())
    return df[COLUMNS]