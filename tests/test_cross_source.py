"""Tests for the cross-source temperature check."""

import pandas as pd

from weatherflow.validate import check_cross_source


def make_rows(city_temps):
    """Rows for one hour: city_temps is {city: temperature}."""
    hour = pd.Timestamp("2026-11-22 12:00", tz="UTC")
    return pd.DataFrame({
        "city": list(city_temps),
        "observed_at_utc": [hour] * len(city_temps),
        "temperature_c": list(city_temps.values()),
    })


def test_sources_that_agree_pass():
    mine = make_rows({"London": 8.0, "Cardiff": 9.0})
    other = make_rows({"London": 9.5, "Cardiff": 8.0})

    result = check_cross_source(mine, other, max_gap_c=3)

    assert result.passed
    assert result.severity == "warn"


def test_big_gap_is_counted_and_the_worst_city_is_named():
    mine = make_rows({"London": 8.0, "Cardiff": 9.0, "Edinburgh": 2.0})
    other = make_rows({"London": 14.0, "Cardiff": 9.5, "Edinburgh": 6.0})   # gaps: 6.0, 0.5, 4.0

    result = check_cross_source(mine, other, max_gap_c=3)

    assert not result.passed
    assert result.failed_rows == 2
    assert "worst city: London" in result.details


def test_nothing_to_compare_is_not_a_failure():
    mine = make_rows({"London": 8.0})

    assert check_cross_source(mine, None, max_gap_c=3).passed
    assert check_cross_source(mine, mine.iloc[0:0], max_gap_c=3).passed