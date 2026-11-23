"""Shared fixtures. pytest finds this file by itself, so tests can just ask for a fixture by name."""

import json
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg
import pytest
from dotenv import load_dotenv

from weatherflow.reference import load_wmo_codes
from weatherflow.transform import transform


@pytest.fixture
def london_payload():
    """One real Open-Meteo response for London, trimmed to 6 hours."""
    path = Path(__file__).parent / "fixtures" / "open_meteo_london.json"
    return json.loads(path.read_text(encoding="utf-8"))   # Windows defaults to cp1252, which garbles "°C"


@pytest.fixture
def wmo_codes():
    """The weather code lookup table (code -> description and category)."""
    return load_wmo_codes()


@pytest.fixture
def dq_config():
    """A small config for the data quality checks: one city, six hours expected."""
    return {
        "cities": [{"name": "London"}],
        "data_quality": {
            "temperature_c": {"min": -30, "max": 45},
            "humidity_pct": {"min": 0, "max": 100},
            "feels_like_max_gap_c": 15,
            "max_data_age_hours": 3,
            "min_hours_per_run": 6,
        },
    }


@pytest.fixture
def clean_df(london_payload, wmo_codes):
    """Six clean London hours, moved in time so the newest hour is the current hour."""
    df = transform([("London", london_payload)], wmo_codes)
    shift = pd.Timestamp.now(tz="UTC").floor("h") - df["observed_at_utc"].max()
    df["observed_at_utc"] = df["observed_at_utc"] + shift
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert("Europe/London")
    return df.reset_index(drop=True)


@pytest.fixture
def warehouse_url(monkeypatch):
    """A throwaway schema inside the PostgreSQL container, so tests never touch the real tables.

    Needs `docker compose up -d warehouse`. If the database is not running, the test is skipped.
    """
    load_dotenv()
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set")

    schema = f"test_{uuid.uuid4().hex[:8]}"
    try:
        admin = psycopg.connect(base_url, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as error:
        pytest.skip(f"PostgreSQL is not reachable ({type(error).__name__}): run docker compose up -d warehouse")

    admin.execute(f"CREATE SCHEMA {schema}")
    test_url = psycopg.conninfo.make_conninfo(base_url, options=f"-c search_path={schema}")
    monkeypatch.setenv("DATABASE_URL", test_url)     # load() reads DATABASE_URL, so it uses the test schema
    yield test_url
    admin.execute(f"DROP SCHEMA {schema} CASCADE")
    admin.close()