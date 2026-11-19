"""Tests for validate.py"""

import pandas as pd
import pytest

from weatherflow.validate import DataQualityError, raise_if_blocking_failures, validate


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