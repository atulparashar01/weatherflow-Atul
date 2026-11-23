"""Tests for the high-water mark used by incremental runs (PostgreSQL, throwaway schema)."""

from pathlib import Path

import pandas as pd
import psycopg

from weatherflow.load import get_high_water_mark, load

SCHEMA_PATH = Path(__file__).parents[1] / "sql" / "schema_postgres.sql"
CITIES = [{"name": "London", "country": "England", "latitude": 51.5085, "longitude": -0.1257}]
DIM_DATE = {"start": "2025-01-01", "end": "2027-12-31"}
SOURCE = "open_meteo_forecast"


def test_high_water_mark_ignores_future_forecast_hours(clean_df, warehouse_url):
    # Six hours: 08:00 to 13:00 UTC. At 10:30 the hours 11:00, 12:00 and 13:00 are still in the future.
    clean_df["observed_at_utc"] = pd.date_range("2026-11-19 08:00", periods=6, freq="h", tz="UTC")
    clean_df["observed_at_local"] = clean_df["observed_at_utc"].dt.tz_convert("Europe/London")
    load(clean_df, CITIES, DIM_DATE, SCHEMA_PATH, SOURCE)
    now = pd.Timestamp("2026-11-19 10:30", tz="UTC").to_pydatetime()

    with psycopg.connect(warehouse_url) as conn:
        mark = get_high_water_mark(conn, "London", SOURCE, now)

    assert mark == pd.Timestamp("2026-11-19 10:00", tz="UTC")


def test_high_water_mark_is_none_when_nothing_is_loaded(warehouse_url):
    now = pd.Timestamp("2026-11-19 10:30", tz="UTC").to_pydatetime()

    with psycopg.connect(warehouse_url) as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        mark = get_high_water_mark(conn, "London", SOURCE, now)

    assert mark is None