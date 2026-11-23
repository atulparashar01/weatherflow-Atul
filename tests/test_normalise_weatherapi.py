import json
from pathlib import Path

import pytest

from weatherflow.reference import load_weatherapi_codes
from weatherflow.transform import add_weather_description, normalise_weatherapi


@pytest.fixture
def weatherapi_payload():
    """One real WeatherAPI response for London, trimmed to 6 hours (no key)."""
    path = Path(__file__).parent / "fixtures" / "weatherapi_london.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_normalise_gives_one_row_per_hour_with_our_columns(weatherapi_payload):
    df = normalise_weatherapi(weatherapi_payload, "London")

    assert len(df) == 6
    assert {"city", "observed_at_utc", "temperature_c", "feels_like_c", "humidity_pct",
            "precipitation_mm", "wind_speed_kmh", "weather_code", "is_daylight"} <= set(df.columns)


def test_normalise_uses_time_epoch_as_utc_and_copies_the_values(weatherapi_payload):
    df = normalise_weatherapi(weatherapi_payload, "London")
    first = weatherapi_payload["forecast"]["forecastday"][0]["hour"][0]

    assert df["observed_at_utc"].iloc[0].timestamp() == first["time_epoch"]
    assert str(df["observed_at_utc"].dt.tz) == "UTC"
    assert df["temperature_c"].iloc[0] == first["temp_c"]
    assert df["wind_speed_kmh"].iloc[0] == first["wind_kph"]
    assert df["weather_code"].iloc[0] == first["condition"]["code"]


def test_every_weatherapi_code_in_the_fixture_has_a_category(weatherapi_payload):
    df = normalise_weatherapi(weatherapi_payload, "London")
    df = add_weather_description(df, load_weatherapi_codes())

    assert "unknown" not in set(df["weather_category"])