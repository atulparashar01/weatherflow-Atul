"""Tests for the WeatherAPI part of extract.py. The real API is never called."""

import logging

import pytest
import requests

from weatherflow.extract import MissingKeyError, extract_weatherapi

KEY = "SECRETKEY123"
CITIES = [{"name": "London", "latitude": 51.5085, "longitude": -0.1257}]
WEATHERAPI = {"forecast_url": "https://example.invalid/forecast.json", "days": 1}
API = {"timeout_seconds": 10, "max_retries": 3}


class FakeResponse:
    """Looks like a failed response. Its error message contains the URL with the key, like the real one."""

    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        raise requests.HTTPError(
            f"{self.status_code} Error for url: https://example.invalid/forecast.json?key={KEY}",
            response=self,
        )


def test_missing_key_stops_the_run_before_any_request(monkeypatch, tmp_path):
    monkeypatch.setattr("weatherflow.extract.load_dotenv", lambda: None)   # do not read the real .env
    monkeypatch.delenv("WEATHERAPI_KEY", raising=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("a request was sent without a key")

    monkeypatch.setattr("weatherflow.extract.requests.get", fail_if_called)

    with pytest.raises(MissingKeyError, match="WEATHERAPI_KEY"):
        extract_weatherapi(CITIES, WEATHERAPI, API, tmp_path)


@pytest.mark.parametrize("status, expected_calls", [(401, 1), (503, 4)])
def test_errors_are_retried_correctly_and_the_key_is_never_logged(
        status, expected_calls, monkeypatch, tmp_path, caplog):
    monkeypatch.setattr("weatherflow.extract.load_dotenv", lambda: None)
    monkeypatch.setenv("WEATHERAPI_KEY", KEY)
    monkeypatch.setattr("weatherflow.extract.time.sleep", lambda seconds: None)
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse(status)

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)

    with caplog.at_level(logging.DEBUG):
        results, failed = extract_weatherapi(CITIES, WEATHERAPI, API, tmp_path)

    assert calls["n"] == expected_calls          # 401: no retry. 503: first try + 3 retries
    assert failed == ["London"]
    assert KEY not in caplog.text