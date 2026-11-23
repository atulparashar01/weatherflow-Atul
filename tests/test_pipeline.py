"""Tests for run_pipeline: the three ways a run stops before any data is touched. No database or API is used."""

import psycopg
import pytest

from weatherflow.pipeline import run_pipeline


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """Do not read the real .env file: each test sets the variables it needs."""
    monkeypatch.setattr("weatherflow.load.load_dotenv", lambda: None)
    monkeypatch.setattr("weatherflow.extract.load_dotenv", lambda: None)


def test_run_stops_with_1_when_database_url_is_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert run_pipeline("open_meteo") == 1


def test_run_stops_with_1_when_the_weatherapi_key_is_missing(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5433/db")
    monkeypatch.delenv("WEATHERAPI_KEY", raising=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("a request was sent without a key")

    monkeypatch.setattr("weatherflow.extract.requests.get", fail_if_called)

    assert run_pipeline("weatherapi") == 1


def test_run_stops_with_1_when_the_database_cannot_be_reached(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5433/db")

    def database_is_down(config, run_time):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr("weatherflow.pipeline.run_open_meteo", database_is_down)

    assert run_pipeline("open_meteo") == 1