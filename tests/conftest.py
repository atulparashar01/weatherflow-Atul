"""Shared fixtures. pytest finds this file by itself, so tests can just ask for a fixture by name."""

import json
from pathlib import Path

import pytest

from weatherflow.reference import load_wmo_codes


@pytest.fixture
def london_payload():
    """One real Open-Meteo response for London, trimmed to 6 hours."""
    path = Path(__file__).parent / "fixtures" / "open_meteo_london.json"
    return json.loads(path.read_text(encoding="utf-8"))   # Windows defaults to cp1252, which garbles "°C"


@pytest.fixture
def wmo_codes():
    """The weather code lookup table (code -> description and category)."""
    return load_wmo_codes()