"""Tests for transform.py"""

import pandas as pd
import pytest

from weatherflow.transform import (
    add_derived_metrics,
    add_weather_description,
    classify_outdoor_risk,
    deduplicate,
    flatten_payload,
)


def test_flatten_payload_returns_one_row_per_hour(london_payload):
    df = flatten_payload(london_payload, "London")

    assert len(df) == 6


def test_flatten_payload_has_city_and_every_hourly_column(london_payload):
    df = flatten_payload(london_payload, "London")

    assert set(df.columns) == set(london_payload["hourly"]) | {"city"}


@pytest.mark.parametrize("celsius, fahrenheit", [(0, 32), (100, 212)])
def test_temperature_is_converted_to_fahrenheit(celsius, fahrenheit):
    df = pd.DataFrame({
        "temperature_c": [float(celsius)],
        "wind_speed_kmh": [0.0],
        "precipitation_mm": [0.0],
        "weather_category": ["clear"],
    })

    result = add_derived_metrics(df)

    assert result["temperature_f"].iloc[0] == pytest.approx(fahrenheit)


def test_unknown_weather_code_becomes_unknown(wmo_codes):
    df = pd.DataFrame({"weather_code": [999]})

    result = add_weather_description(df, wmo_codes)

    assert result["weather_description"].iloc[0] == "unknown"


def test_deduplicate_keeps_the_latest_ingested_row():
    hour = pd.Timestamp("2026-11-19 10:00", tz="UTC")
    df = pd.DataFrame({
        "city": ["London", "London"],
        "observed_at_utc": [hour, hour],
        "temperature_c": [5.0, 6.0],
        "ingested_at_utc": ["2026-11-19T12:00:00+00:00", "2026-11-19T09:00:00+00:00"],
    })

    result = deduplicate(df)

    assert len(result) == 1
    assert result["temperature_c"].iloc[0] == 5.0      # the row ingested at 12:00 wins


def risk_for(beaufort=0, category="clear", rain=0.0, temp=10.0):
    """Build a one-row table and return its outdoor_work_risk."""
    df = pd.DataFrame({
        "beaufort_scale": pd.array([beaufort], dtype="Int64"),
        "weather_category": [category],
        "precipitation_mm": [rain],
        "temperature_c": [temp],
    })
    return classify_outdoor_risk(df).iloc[0]


@pytest.mark.parametrize(
    "inputs, expected",
    [
        pytest.param({}, "low", id="calm_mild_is_low"),
        # high rules and their boundaries
        pytest.param({"rain": 4.0}, "high", id="rain_exactly_4mm_is_high"),
        pytest.param({"rain": 3.9}, "medium", id="rain_just_under_4mm_is_medium"),
        pytest.param({"beaufort": 7}, "high", id="beaufort_exactly_7_is_high"),
        pytest.param({"beaufort": 6}, "medium", id="beaufort_6_is_medium"),
        pytest.param({"category": "storm"}, "high", id="storm_is_high"),
        pytest.param({"category": "snow"}, "high", id="snow_is_high"),
        # medium rules and their boundaries
        pytest.param({"rain": 1.0}, "medium", id="rain_exactly_1mm_is_medium"),
        pytest.param({"rain": 0.9}, "low", id="rain_just_under_1mm_is_low"),
        pytest.param({"beaufort": 5}, "medium", id="beaufort_exactly_5_is_medium"),
        pytest.param({"beaufort": 4}, "low", id="beaufort_4_is_low"),
        pytest.param({"temp": 0.0}, "medium", id="exactly_0_degrees_is_medium"),
        pytest.param({"temp": 0.1}, "low", id="just_above_0_degrees_is_low"),
    ],
)
def test_outdoor_work_risk_rules_and_boundaries(inputs, expected):
    assert risk_for(**inputs) == expected