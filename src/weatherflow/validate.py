"""Data quality checks. They run between transform and load.

How it works:
  1. Small "find_..." functions return a True/False column (True = bad row).
  2. validate() runs all the checks, separates the bad rows and builds a report card for each check.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE = "open_meteo_forecast"


class DataQualityError(Exception):
    """Raised when a blocking check fails. It stops the run before loading."""


@dataclass
class CheckResult:
    """The report card of one check."""

    name: str          # for example "temperature_in_range"
    dimension: str     # completeness, validity, uniqueness, timeliness, consistency
    severity: str      # "quarantine", "fail" or "warn"
    passed: bool       # True if nothing was wrong
    failed_rows: int   # how many problems were found
    details: str       # a sentence a human can read


# ---------- Row checks: return True for every BAD row ----------

def find_missing_values(df):
    """Check 1: city, observed_at_utc and temperature_c must not be empty."""
    return df[["city", "observed_at_utc", "temperature_c"]].isna().any(axis=1)


def find_bad_temperature(df, limits):
    """Check 2: temperature must be between min and max."""
    return (df["temperature_c"] < limits["min"]) | (df["temperature_c"] > limits["max"])


def find_bad_humidity(df, limits):
    """Check 3: humidity must be between min and max."""
    return (df["humidity_pct"] < limits["min"]) | (df["humidity_pct"] > limits["max"])


def find_negative_values(df):
    """Check 4: rain and wind can't be below zero."""
    return (df["precipitation_mm"] < 0) | (df["wind_speed_kmh"] < 0)


def find_big_feels_like_gap(df, max_gap):
    """Check 8: feels-like should be close to the real temperature."""
    return (df["feels_like_c"] - df["temperature_c"]).abs() > max_gap


# ---------- Dataset checks: look at the whole table, return a CheckResult ----------

def check_duplicates(df) -> CheckResult:
    """Check 5: one row per (city, observed_at_utc, source)."""
    count = int(df.duplicated(subset=["city", "observed_at_utc", "source"]).sum())
    details = f"{count} duplicate row(s)" if count else "ok"
    return CheckResult("no_duplicate_rows", "uniqueness", "fail", count == 0, count, details)


def check_missing_hours(df, city_names, min_hours) -> CheckResult:
    """Check 6: every city must have a row for every hour of this run."""
    name, dimension, severity = "every_city_has_every_hour", "completeness", "fail"

    if df.empty:
        return CheckResult(name, dimension, severity, False, 0, "no rows at all")

    # Every hour from the first to the last hour in the data
    hours = pd.date_range(df["observed_at_utc"].min(), df["observed_at_utc"].max(), freq="h")
    if len(hours) < min_hours:
        details = f"run covers only {len(hours)} hours, expected at least {min_hours}"
        return CheckResult(name, dimension, severity, False, 0, details)

    # The (city, hour) pairs we have, and the ones that are missing
    have = set(zip(df["city"], df["observed_at_utc"]))
    missing = [(city, hour) for city in city_names for hour in hours if (city, hour) not in have]

    if not missing:
        return CheckResult(name, dimension, severity, True, 0, "ok")
    city, hour = missing[0]
    details = f"{len(missing)} missing city-hour(s), for example {city} at {hour:%Y-%m-%d %H:%M}"
    return CheckResult(name, dimension, severity, False, len(missing), details)


def check_freshness(df, max_age_hours, now=None) -> CheckResult:
    """Check 7: the newest reading that is not in the future must be recent."""
    name, dimension, severity = "latest_reading_is_recent", "timeliness", "warn"
    now = now if now is not None else pd.Timestamp.now(tz="UTC")

    past = df.loc[df["observed_at_utc"] <= now, "observed_at_utc"]   # forecast rows are ignored
    if past.empty:
        return CheckResult(name, dimension, severity, False, 1, "no readings from the past")

    age_hours = (now - past.max()).total_seconds() / 3600
    if age_hours > max_age_hours:
        details = f"latest reading is {age_hours:.1f} hours old (limit {max_age_hours})"
        return CheckResult(name, dimension, severity, False, 1, details)
    return CheckResult(name, dimension, severity, True, 0, "ok")


# ---------- Put it all together ----------

def validate(df: pd.DataFrame, config: dict, source: str = SOURCE, check_freshness_too: bool = True):
    """Run every check. Return (good_rows, quarantined_rows, results).

    The freshness check is for normal runs only. A backfill loads old data, so it skips it.
    """
    limits = config["data_quality"]
    city_names = [city["name"] for city in config["cities"]]

    df = df.assign(source=source)

    # name, dimension, severity, which rows are bad, what to say about them
    row_checks = [
        ("required_fields_not_null", "completeness", "quarantine",
         find_missing_values(df), "have a missing city, time or temperature"),
        ("temperature_in_range", "validity", "quarantine",
         find_bad_temperature(df, limits["temperature_c"]), "have a temperature outside the allowed range"),
        ("humidity_in_range", "validity", "quarantine",
         find_bad_humidity(df, limits["humidity_pct"]), "have humidity outside the allowed range"),
        ("rain_and_wind_not_negative", "validity", "quarantine",
         find_negative_values(df), "have negative rain or wind"),
        ("feels_like_close_to_temperature", "consistency", "warn",
         find_big_feels_like_gap(df, limits["feels_like_max_gap_c"]), "have a feels-like far from the temperature"),
    ]

    results = []
    reasons = pd.Series("", index=df.index)      # one text per row, empty = row is fine

    for name, dimension, severity, bad, message in row_checks:
        count = int(bad.sum())
        details = f"{count} row(s) {message}" if count else "ok"
        results.append(CheckResult(name, dimension, severity, count == 0, count, details))
        if severity == "quarantine":
            reasons[bad] = reasons[bad] + name + "; "     # add the reason to the bad rows

    results.append(check_duplicates(df))
    results.append(check_missing_hours(df, city_names, limits["min_hours_per_run"]))
    if check_freshness_too:
        results.append(check_freshness(df, limits["max_data_age_hours"]))

    # Split the table in two
    is_bad = reasons != ""
    good_rows = df[~is_bad]
    quarantined_rows = df[is_bad].assign(dq_failure_reason=reasons[is_bad].str.rstrip("; "))

    for r in results:
        if not r.passed:
            logger.warning("DQ check %s (%s): %s", r.name, r.severity, r.details)
    logger.info("Validation: %d good rows, %d quarantined rows", len(good_rows), len(quarantined_rows))

    return good_rows, quarantined_rows, results


def raise_if_blocking_failures(results) -> None:
    """Stop the run if any check with severity "fail" did not pass."""
    failed = [r for r in results if r.severity == "fail" and not r.passed]
    if failed:
        message = "; ".join(f"{r.name}: {r.details}" for r in failed)
        raise DataQualityError(f"Blocking data quality check failed - {message}")


# ---------- Save the evidence ----------

def write_quarantine(quarantined: pd.DataFrame, quarantine_dir, run_time: datetime, source: str = ""):
    """Save the quarantined rows (with their reason) as a CSV file."""
    if quarantined.empty:
        return None
    folder = Path(quarantine_dir) / f"run_date={run_time:%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    tag = f"_{source}" if source else ""       # two sources in one run must not overwrite each other
    path = folder / f"quarantine-{run_time:%Y%m%dT%H%M%S}{tag}.csv"
    quarantined.to_csv(path, index=False)
    logger.warning("Quarantined %d rows, saved to %s", len(quarantined), path)
    return path


def write_dq_report(results, good_rows, quarantined_rows, report_dir, run_time: datetime,
                    source: str = "") -> Path:
    """Write a Markdown summary of this run to docs/dq_reports/."""
    if any(r.severity == "fail" and not r.passed for r in results):
        status = "FAILED (run stopped before loading)"
    elif any(not r.passed for r in results):
        status = "PASSED WITH WARNINGS"
    else:
        status = "PASSED"

    lines = [
        f"# Data quality report - {run_time:%Y-%m-%d %H:%M:%S} UTC",
        "",
        f"- **Source:** {source or 'not given'}",
        f"- **Status:** {status}",
        f"- **Rows checked:** {len(good_rows) + len(quarantined_rows)}",
        f"- **Good rows:** {len(good_rows)}",
        f"- **Quarantined rows:** {len(quarantined_rows)}",
        "",
        "| Check | Dimension | Severity | Result | Failed rows | Details |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        outcome = "pass" if r.passed else "FAIL"
        lines.append(f"| {r.name} | {r.dimension} | {r.severity} | {outcome} | {r.failed_rows} | {r.details} |")

    folder = Path(report_dir)
    folder.mkdir(parents=True, exist_ok=True)
    tag = f"_{source}" if source else ""
    path = folder / f"{run_time:%Y%m%dT%H%M%S}{tag}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("DQ report written to %s", path)
    return path