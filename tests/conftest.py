"""Shared fixtures. pytest finds this file by itself, so tests can just ask for a fixture by name."""

import json
from pathlib import Path

import pandas as pd
import pytest

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