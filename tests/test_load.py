"""Integration test: transform + load into a real SQLite database (in a temporary folder)."""

import sqlite3
from pathlib import Path

from weatherflow.load import load
from weatherflow.transform import transform

SCHEMA_PATH = Path(__file__).parents[1] / "sql" / "schema.sql"
CITIES = [{"name": "London", "country": "England", "latitude": 51.5085, "longitude": -0.1257}]
DIM_DATE = {"start": "2025-01-01", "end": "2027-12-31"}


def count_fact_rows(db_path):
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM fact_weather_hourly").fetchone()[0]
    conn.close()
    return count


def test_loading_the_same_data_twice_does_not_change_the_row_count(london_payload, wmo_codes, tmp_path):
    df = transform([("London", london_payload)], wmo_codes)
    db_path = tmp_path / "test_weather.db"

    load(df, CITIES, DIM_DATE, db_path, SCHEMA_PATH)
    rows_after_first_load = count_fact_rows(db_path)
    load(df, CITIES, DIM_DATE, db_path, SCHEMA_PATH)
    rows_after_second_load = count_fact_rows(db_path)

    assert rows_after_first_load == 6
    assert rows_after_second_load == rows_after_first_load