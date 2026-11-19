"""Tests for transform.py"""

from weatherflow.transform import flatten_payload


def test_flatten_payload_returns_one_row_per_hour(london_payload):
    df = flatten_payload(london_payload, "London")

    assert len(df) == 6


def test_flatten_payload_has_city_and_every_hourly_column(london_payload):
    df = flatten_payload(london_payload, "London")

    expected = set(london_payload["hourly"]) | {"city"}
    assert set(df.columns) == expected