"""Integration test: transform + load into PostgreSQL (a throwaway schema, see conftest.py)."""

from pathlib import Path

import psycopg

from weatherflow.load import load
from weatherflow.transform import transform

SCHEMA_PATH = Path(__file__).parents[1] / "sql" / "schema_postgres.sql"
CITIES = [{"name": "London", "country": "England", "latitude": 51.5085, "longitude": -0.1257}]
DIM_DATE = {"start": "2025-01-01", "end": "2027-12-31"}


def count_fact_rows(url):
    with psycopg.connect(url) as conn:
        return conn.execute("SELECT COUNT(*) FROM fact_weather_hourly").fetchone()[0]


def test_loading_the_same_data_twice_does_not_change_the_row_count(london_payload, wmo_codes, warehouse_url):
    df = transform([("London", london_payload)], wmo_codes)

    load(df, CITIES, DIM_DATE, SCHEMA_PATH)
    rows_after_first_load = count_fact_rows(warehouse_url)
    load(df, CITIES, DIM_DATE, SCHEMA_PATH)
    rows_after_second_load = count_fact_rows(warehouse_url)

    assert rows_after_first_load == 6
    assert rows_after_second_load == rows_after_first_load