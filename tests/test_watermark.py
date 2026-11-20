"""Tests for the high-water mark used by incremental runs."""

import sqlite3
from pathlib import Path

import pandas as pd

from weatherflow.load import get_high_water_mark, load

SCHEMA_PATH = Path(__file__).parents[1] / "sql" / "schema.sql"
CITIES = [{"name": "London", "country": "England", "latitude": 51.5085, "longitude": -0.1257}]
DIM_DATE = {"start": "2025-01-01", "end": "2027-12-31"}
SOURCE = "open_meteo_forecast"


def test_high_water_mark_ignores_future_forecast_hours(clean_df, tmp_path):
    # Six hours: 08:00 to 13:00 UTC. At 10:30 the hours 11:00, 12:00 and 13:00 are still in the future.
    clean_df["observed_at_utc"] = pd.date_range("2026-11-19 08:00", periods=6, freq="h", tz="UTC")
    clean_df["observed_at_local"] = clean_df["observed_at_utc"].dt.tz_convert("Europe/London")
    db_path = tmp_path / "test_weather.db"
    load(clean_df, CITIES, DIM_DATE, db_path, SCHEMA_PATH, SOURCE)
    now = pd.Timestamp("2026-11-19 10:30", tz="UTC").to_pydatetime()

    conn = sqlite3.connect(db_path)
    mark = get_high_water_mark(conn, "London", SOURCE, now)
    conn.close()

    assert mark == pd.Timestamp("2026-11-19 10:00", tz="UTC")


def test_high_water_mark_is_none_when_nothing_is_loaded(tmp_path):
    conn = sqlite3.connect(tmp_path / "empty.db")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    now = pd.Timestamp("2026-11-19 10:30", tz="UTC").to_pydatetime()

    mark = get_high_water_mark(conn, "London", SOURCE, now)
    conn.close()

    assert mark is None