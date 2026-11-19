"""Wires the steps together: extract -> transform -> validate -> load."""
import logging
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

from weatherflow.config import load_config
from weatherflow.extract import extract_all, fetch_city_range, save_raw
from weatherflow.load import load, write_parquet
from weatherflow.reference import load_wmo_codes
from weatherflow.transform import transform
from weatherflow.validate import (
    DataQualityError,
    raise_if_blocking_failures,
    validate,
    write_dq_report,
    write_quarantine,
)

logger = logging.getLogger(__name__)

SOURCE_FORECAST = "open_meteo_forecast"
SOURCE_ARCHIVE = "open_meteo_archive"


def process_and_load(raw, config, source, run_time, is_normal_run) -> int:
    """Transform -> validate -> load. Both run and backfill use this. Return 0 or 1."""
    paths = config["paths"]

    df = transform(raw, load_wmo_codes())

    good, quarantined, results = validate(df, config, source, check_freshness_too=is_normal_run)
    write_quarantine(quarantined, paths["quarantine_dir"], run_time)
    write_dq_report(results, good, quarantined, paths["dq_reports_dir"], run_time)

    try:
        raise_if_blocking_failures(results)
    except DataQualityError as error:
        logger.error("Run FAILED: %s", error)
        return 1

    load(good, config["cities"], config["dim_date"], paths["database"], paths["schema"], source)
    write_parquet(good, paths["processed_dir"], run_time)
    return 0


def run_pipeline() -> int:
    """Normal run: yesterday and today. Return 0 if everything worked, 1 if not."""
    config = load_config()
    paths = config["paths"]
    run_time = datetime.now(timezone.utc)
    logger.info("Pipeline started")

    status = 0
    raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"])
    if raw:
        status = process_and_load(raw, config, SOURCE_FORECAST, run_time, is_normal_run=True)

    if failed:
        logger.error("Run FAILED: no data for %s", ", ".join(failed))
        return 1
    if status == 0:
        logger.info("Run succeeded")
    return status


def run_backfill(days: int, start_date: date = None, end_date: date = None) -> int:
    """Load history from the archive API, in chunks. Return 0 if it worked, 1 if not."""
    config = load_config()
    api, paths, settings = config["api"], config["paths"], config["backfill"]
    run_time = datetime.now(timezone.utc)

    # The archive trails real time, so by default we stop a few days before today
    if end_date is None:
        end_date = run_time.date() - timedelta(days=settings["lag_days"])
    if start_date is None:
        start_date = end_date - timedelta(days=days - 1)
    logger.info("Backfill started: %s to %s", start_date, end_date)

    chunk_days = settings["chunk_days"]
    raw, failed = [], []
    for city in config["cities"]:
        for chunk_start in pd.date_range(start_date, end_date, freq=f"{chunk_days}D"):
            chunk_start = chunk_start.date()
            chunk_end = min(chunk_start + timedelta(days=chunk_days - 1), end_date)
            try:
                payload = fetch_city_range(city, api, api["archive_url"], chunk_start, chunk_end)
            except requests.RequestException as error:
                logger.error("%s: %s to %s failed: %s", city["name"], chunk_start, chunk_end, error)
                failed.append(f"{city['name']} {chunk_start}")
                continue
            save_raw(f"{city['name']}_{chunk_start}", payload, paths["raw_dir"])
            raw.append((city["name"], payload))
            time.sleep(settings["pause_seconds"])         # be polite to the free API

    if failed:
        logger.error("Backfill FAILED: no data for %s", ", ".join(failed))
        return 1

    status = process_and_load(raw, config, SOURCE_ARCHIVE, run_time, is_normal_run=False)
    if status == 0:
        logger.info("Backfill succeeded")
    return status