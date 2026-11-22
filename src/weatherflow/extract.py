"""Extract step: call the Open-Meteo API and save the raw JSON unchanged."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class MissingKeyError(RuntimeError):
    """The WeatherAPI key is not set."""


def _describe(error: Exception) -> str:
    """Short text for logs: the error type and status code. Never the URL, which holds the API key."""
    status = getattr(getattr(error, "response", None), "status_code", None)
    name = type(error).__name__
    return f"{name} (status {status})" if status else name


def _get_json(url: str, params: dict, name: str, api: dict) -> dict:
    """GET a URL and return its JSON. Retry temporary failures with backoff (1s, 2s, 4s)."""
    max_retries = api["max_retries"]

    for attempt in range(max_retries + 1):          # 1 first try + max_retries retries
        try:
            response = requests.get(url, params=params, timeout=api["timeout_seconds"])
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            if err.response is not None and err.response.status_code < 500:
                raise                                # 4xx: our request is wrong, no retry
            error = err                              # 5xx: server problem, retry
        except (requests.Timeout, requests.ConnectionError) as err:
            error = err                              # temporary problem, retry

        if attempt < max_retries:
            wait = 2 ** attempt                      # 1s, 2s, 4s
            logger.warning("%s: attempt %d failed (%s); retrying in %ds",
                           name, attempt + 1, _describe(error), wait)
            time.sleep(wait)

    raise error                                      # all tries failed


def fetch_city(city: dict, api: dict) -> dict:
    """Fetch one city's forecast: yesterday and today."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api["hourly_variables"]),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": api["timezone"],
    }
    return _get_json(api["forecast_url"], params, city["name"], api)


def fetch_city_range(city: dict, api: dict, url: str, start_date, end_date) -> dict:
    """Fetch one city for a date range (start_date and end_date are both included).

    Use api["archive_url"] for history and api["forecast_url"] for recent days.
    """
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api["hourly_variables"]),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "timezone": api["timezone"],
    }
    logger.info("%s: requesting %s to %s from %s", city["name"], start_date, end_date, url)
    return _get_json(url, params, city["name"], api)


def save_raw(city_name: str, payload: dict, raw_dir: Path) -> Path:
    """Write the payload unchanged to <raw_dir>/<date>/<city>_<timestamp>.json."""
    now = datetime.now(timezone.utc)
    folder = raw_dir / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_name.lower()}_{now.strftime('%Y%m%dT%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def extract_all(cities: list[dict], api: dict, raw_dir: Path,
                start_date=None, end_date=None) -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch and save every city. Return (good results, names of cities that failed).

    Without dates: yesterday and today (past_days=1). With dates: that range, from the forecast API.
    """
    results, failed = [], []
    for city in cities:
        try:
            if start_date is None:
                payload = fetch_city(city, api)
            else:
                payload = fetch_city_range(city, api, api["forecast_url"], start_date, end_date)
        except requests.RequestException as err:
            logger.error("%s: giving up: %s", city["name"], err)
            failed.append(city["name"])
            continue
        path = save_raw(city["name"], payload, raw_dir)
        logger.info("%s: %d hourly records saved to %s",
                    city["name"], len(payload["hourly"]["time"]), path)
        results.append((city["name"], payload))
    return results, failed


def get_weatherapi_key() -> str:
    """Read WEATHERAPI_KEY from .env or the environment. Stop with a clear message if it is missing."""
    load_dotenv()
    key = os.getenv("WEATHERAPI_KEY")
    if not key:
        raise MissingKeyError(
            "WEATHERAPI_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key


def fetch_weatherapi_city(city: dict, weatherapi: dict, api: dict, key: str) -> dict:
    """Fetch one city from WeatherAPI. The key is in the request, so never log the URL."""
    params = {
        "key": key,
        "q": f"{city['latitude']},{city['longitude']}",
        "days": weatherapi["days"],
    }
    return _get_json(weatherapi["forecast_url"], params, city["name"], api)


def extract_weatherapi(cities: list[dict], weatherapi: dict, api: dict,
                       raw_dir: Path) -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch and save every city from WeatherAPI. Return (good results, names of cities that failed).

    Raises MissingKeyError before any request is sent if the key is missing.
    """
    key = get_weatherapi_key()
    results, failed = [], []
    for city in cities:
        try:
            payload = fetch_weatherapi_city(city, weatherapi, api, key)
        except requests.RequestException as err:
            logger.error("%s: WeatherAPI giving up: %s", city["name"], _describe(err))
            failed.append(city["name"])
            continue
        path = save_raw(f"{city['name']}_weatherapi", payload, raw_dir)
        hours = sum(len(day["hour"]) for day in payload["forecast"]["forecastday"])
        logger.info("%s: %d hourly records from WeatherAPI saved to %s", city["name"], hours, path)
        results.append((city["name"], payload))
    return results, failed
