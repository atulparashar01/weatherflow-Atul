"""Tests for validate.py"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from weatherflow.validate import (
    DataQualityError,
    raise_if_blocking_failures,
    validate,
    write_dq_report,
    write_quarantine,
)


def test_clean_data_passes_every_check(clean_df, dq_config):
    good, quarantined, results = validate(clean_df, dq_config)

    assert all(r.passed for r in results)
    assert len(good) == 6
    assert quarantined.empty


def test_99_degree_reading_is_quarantined_with_the_right_reason(clean_df, dq_config):
    clean_df.loc[0, ["temperature_c", "feels_like_c"]] = 99.0

    good, quarantined, _ = validate(clean_df, dq_config)

    assert len(good) == 5
    assert quarantined["dq_failure_reason"].tolist() == ["temperature_in_range"]


def test_duplicate_row_raises_data_quality_error(clean_df, dq_config):
    duplicated = pd.concat([clean_df, clean_df.iloc[[0]]], ignore_index=True)

    _, _, results = validate(duplicated, dq_config)

    with pytest.raises(DataQualityError, match="no_duplicate_rows"):
        raise_if_blocking_failures(results)


# The two tests below are not in the task list. They were added to reach the 70% coverage target.

def test_quarantined_rows_are_saved_with_their_reason(clean_df, dq_config, tmp_path):
    clean_df.loc[0, ["temperature_c", "feels_like_c"]] = 99.0
    _, quarantined, _ = validate(clean_df, dq_config)
    run_time = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)

    path = write_quarantine(quarantined, tmp_path, run_time)

    saved = pd.read_csv(path)
    assert saved["dq_failure_reason"].tolist() == ["temperature_in_range"]


def test_dq_report_says_failed_when_a_blocking_check_fails(clean_df, dq_config, tmp_path):
    duplicated = pd.concat([clean_df, clean_df.iloc[[0]]], ignore_index=True)
    good, quarantined, results = validate(duplicated, dq_config)
    run_time = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)

    path = write_dq_report(results, good, quarantined, tmp_path, run_time)

    text = path.read_text(encoding="utf-8")
    assert "FAILED" in text
    assert "no_duplicate_rows" in text