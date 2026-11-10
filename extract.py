"""Extract step: call the Open-Meteo forecast API for five UK cities and
land each raw JSON response, unchanged, under data/raw/<YYYY-MM-DD>/.

Run:  python extract.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://api.open-meteo.com/v1/forecast"
RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"

# Confirm these with the Geocoding API (Step 2) before relying on them.
CITIES = [
    {"name": "London", "latitude": 51.5085, "longitude": -0.1257},
    {"name": "Manchester", "latitude": 53.4809, "longitude": -2.2374},
    {"name": "Birmingham", "latitude": 52.4814, "longitude": -1.8998},
    {"name": "Edinburgh", "latitude": 55.9521, "longitude": -3.1965},
    {"name": "Cardiff", "latitude": 51.4800, "longitude": -3.1800},
]

HOURLY_VARIABLES = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,wind_speed_10m,weather_code"
)


def fetch_city(city: dict) -> dict:
    """Call the forecast API for one city and return the parsed JSON."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": HOURLY_VARIABLES,
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Europe/London",
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()  # turns 4xx/5xx into an exception
    return response.json()


def save_raw(city_name: str, payload: dict) -> Path:
    """Write the payload unchanged to data/raw/<date>/<city>_<timestamp>.json."""
    now = datetime.now(timezone.utc)  # UTC: never shifts with daylight saving
    folder = RAW_DIR / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_name.lower()}_{now.strftime('%Y%m%dT%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)  # indent only changes layout, not values
    return path


def main() -> int:
    saved, failed = 0, 0
    for city in CITIES:
        try:
            payload = fetch_city(city)
            path = save_raw(city["name"], payload)
            records = len(payload.get("hourly", {}).get("time", []))
            print(f"OK    {city['name']}: {records} hourly records -> {path}")
            saved += 1
        except requests.RequestException as err:
            detail = ""
            if getattr(err, "response", None) is not None:
                detail = f" | server said: {err.response.text[:200]}"
            print(f"ERROR {city['name']}: {err}{detail}")
            failed += 1
    print(f"Done: {saved} saved, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())