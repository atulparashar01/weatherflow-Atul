"""Wires the steps together: extract -> transform -> validate -> load."""
import logging
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from weatherflow.config import load_config
from weatherflow.extract import (
    MissingKeyError,
    extract_all,
    extract_weatherapi,
    fetch_city_range,
    get_weatherapi_key,
    save_raw,
)
from weatherflow.load import get_high_water_mark, load, write_parquet
from weatherflow.reference import load_weatherapi_codes, load_wmo_codes
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
SOURCE_WEATHERAPI = "weatherapi_forecast"


def process_and_load(raw, config, source, run_time, is_normal_run) -> int:
    """Transform -> validate -> load. Both run and backfill use this. Return 0 or 1."""
    paths = config["paths"]

    if source == SOURCE_WEATHERAPI:
        df = transform(raw, load_weatherapi_codes(), "weatherapi")
    else:
        df = transform(raw, load_wmo_codes())

    good, quarantined, results = validate(df, config, source, check_freshness_too=is_normal_run)
    write_quarantine(quarantined, paths["quarantine_dir"], run_time, source)
    write_dq_report(results, good, quarantined, paths["dq_reports_dir"], run_time, source)

    try:
        raise_if_blocking_failures(results)
    except DataQualityError as error:
        logger.error("Run FAILED: %s", error)
        return 1

    load(good, config["cities"], config["dim_date"], paths["database"], paths["schema"], source)
    write_parquet(good, paths["processed_dir"], run_time, source)
    return 0


def find_start_date(config: dict, now: datetime):
    """Where should this run start? None means "no high-water mark yet"."""
    db_path = Path(config["paths"]["database"])
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        marks = [get_high_water_mark(conn, city["name"], SOURCE_FORECAST, now)
                 for city in config["cities"]]
    except sqlite3.OperationalError:                  # the tables do not exist yet
        return None
    finally:
        conn.close()

    if any(mark is None for mark in marks):
        return None
    overlap = timedelta(hours=config["incremental"]["overlap_hours"])
    return (min(marks) - overlap).date()


def run_open_meteo(config: dict, run_time: datetime) -> int:
    """Open-Meteo part of a normal run: only what is new. Return 0 or 1."""
    paths = config["paths"]

    start_date = find_start_date(config, run_time)
    if start_date is None:
        logger.info("No high-water mark yet: fetching yesterday and today (past_days=1)")
        raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"])
    else:
        end_date = run_time.date()
        logger.info("High-water mark found: fetching %s to %s", start_date, end_date)
        raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"],
                                  start_date, end_date)

    status = 0
    if raw:
        status = process_and_load(raw, config, SOURCE_FORECAST, run_time, is_normal_run=True)

    if failed:
        logger.error("Open-Meteo FAILED: no data for %s", ", ".join(failed))
        return 1
    return status


def run_weatherapi(config: dict, run_time: datetime) -> int:
    """WeatherAPI part of a normal run (today's 24 hours). Return 0 or 1."""
    raw, failed = extract_weatherapi(config["cities"], config["weatherapi"],
                                     config["api"], config["paths"]["raw_dir"])
    status = 0
    if raw:
        status = process_and_load(raw, config, SOURCE_WEATHERAPI, run_time, is_normal_run=True)

    if failed:
        logger.error("WeatherAPI FAILED: no data for %s", ", ".join(failed))
        return 1
    return status


def run_pipeline(source: str = "all") -> int:
    """Normal run for open_meteo, weatherapi or all. Return 0 if everything worked, 1 if not."""
    config = load_config()
    run_time = datetime.now(timezone.utc)
    logger.info("Pipeline started (source: %s)", source)

    use_open_meteo = source in ("open_meteo", "all")
    use_weatherapi = source in ("weatherapi", "all")

    if use_weatherapi:
        try:
            get_weatherapi_key()              # fail now, before any request is sent
        except MissingKeyError as error:
            logger.error("Run FAILED: %s", error)
            return 1

    status = 0
    if use_open_meteo:
        status = max(status, run_open_meteo(config, run_time))
    if use_weatherapi:
        status = max(status, run_weatherapi(config, run_time))

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