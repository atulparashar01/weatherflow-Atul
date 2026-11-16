"""Extract step: call the Open-Meteo API and save the raw JSON unchanged."""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def fetch_city(city: dict, api: dict) -> dict:
    """Fetch one city's forecast. Retry temporary failures with backoff (1s, 2s, 4s)."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api["hourly_variables"]),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": api["timezone"],
    }
    max_retries = api["max_retries"]

    for attempt in range(max_retries + 1):          # 1 first try + max_retries retries
        try:
            response = requests.get(
                api["forecast_url"], params=params, timeout=api["timeout_seconds"]
            )
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
                           city["name"], attempt + 1, error, wait)
            time.sleep(wait)

    raise error                                      # all tries failed


def save_raw(city_name: str, payload: dict, raw_dir: Path) -> Path:
    """Write the payload unchanged to <raw_dir>/<date>/<city>_<timestamp>.json."""
    now = datetime.now(timezone.utc)
    folder = raw_dir / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_name.lower()}_{now.strftime('%Y%m%dT%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path

def extract_all(cities: list[dict], api: dict, raw_dir: Path) -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch and save every city. Return (good results, names of cities that failed)."""
    results, failed = [], []
    for city in cities:
        try:
            payload = fetch_city(city, api)
        except requests.RequestException as err:
            logger.error("%s: giving up: %s", city["name"], err)
            failed.append(city["name"])
            continue
        path = save_raw(city["name"], payload, raw_dir)
        logger.info("%s: %d hourly records saved to %s",
                    city["name"], len(payload["hourly"]["time"]), path)
        results.append((city["name"], payload))
    return results, failed