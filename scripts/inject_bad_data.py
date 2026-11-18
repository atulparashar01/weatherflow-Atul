"""Prove the data quality gate works by injecting bad data on purpose.

Test 1: a 99 degree reading   -> the row is quarantined, the run continues.
Test 2: a duplicate row       -> the run is stopped before loading.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from weatherflow.config import load_config
from weatherflow.validate import (
    DataQualityError,
    raise_if_blocking_failures,
    validate,
    write_dq_report,
    write_quarantine,
)

config = load_config()
paths = config["paths"]

# Start from real, clean data: the newest Parquet file
newest = sorted(Path(paths["processed_dir"]).glob("weather_hourly/*/*.parquet"))[-1]
clean = pd.read_parquet(newest)
print(f"Clean data: {len(clean)} rows from {newest.name}\n")


def run_gate(data, run_time):
    """Run the same steps as the pipeline, up to the point where it would load."""
    good, quarantined, results = validate(data, config)
    write_quarantine(quarantined, paths["quarantine_dir"], run_time)
    report = write_dq_report(results, good, quarantined, paths["dq_reports_dir"], run_time)
    print(f"   good rows: {len(good)}, quarantined rows: {len(quarantined)}")
    print(f"   report: {report.name}")
    raise_if_blocking_failures(results)        # raises DataQualityError if a 'fail' check failed
    return quarantined


# ---------- Test 1: a 99 degree reading ----------
print("TEST 1: inject a 99 degree reading in Cardiff")
hot = clean.copy()
row = hot.index[hot["city"] == "Cardiff"][0]
hot.loc[row, ["temperature_c", "feels_like_c"]] = 99.0

quarantined = run_gate(hot, datetime.now(timezone.utc))
print(quarantined[["city", "observed_at_utc", "temperature_c", "dq_failure_reason"]].to_string())
print("   -> the bad row was quarantined and the run would continue to the load\n")

# ---------- Test 2: a duplicate row ----------
print("TEST 2: inject a duplicate row")
duplicated = pd.concat([clean, clean.iloc[[0]]], ignore_index=True)

try:
    run_gate(duplicated, datetime.now(timezone.utc) + timedelta(seconds=1))
    print("   -> PROBLEM: the run was not stopped")
except DataQualityError as error:
    print(f"   -> run stopped before loading: {error}")