"""Tests for extract.py. The real API is never called: requests.get is replaced by a fake."""

import json

import pytest
import requests

from weatherflow.extract import fetch_city, save_raw

CITY = {"name": "London", "latitude": 51.5085, "longitude": -0.1257}
API = {
    "forecast_url": "https://example.invalid/forecast",
    "timeout_seconds": 10,
    "max_retries": 3,
    "hourly_variables": ["temperature_2m"],
    "timezone": "UTC",
}


class FakeResponse:
    """Looks like the object requests.get() returns."""

    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


def test_fetch_retries_on_server_error(monkeypatch):
    calls = {"n": 0}
    answers = [FakeResponse(503), FakeResponse(503), FakeResponse(200, {"ok": True})]

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return answers[calls["n"] - 1]

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    monkeypatch.setattr("weatherflow.extract.time.sleep", lambda seconds: None)   # no real waiting

    result = fetch_city(CITY, API)

    assert result == {"ok": True}
    assert calls["n"] == 3


def test_fetch_does_not_retry_on_404(monkeypatch):
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse(404)

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    monkeypatch.setattr("weatherflow.extract.time.sleep", lambda seconds: None)

    with pytest.raises(requests.HTTPError):
        fetch_city(CITY, API)

    assert calls["n"] == 1


def test_save_raw_writes_the_payload_to_tmp_path(tmp_path):
    payload = {"hourly": {"time": ["2026-11-19T00:00"], "temperature_2m": [8.4]}}

    path = save_raw("London", payload, tmp_path)

    assert path.exists()
    assert tmp_path in path.parents
    assert path.name.startswith("london_")
    assert json.loads(path.read_text(encoding="utf-8")) == payload