"""Reference data: small lookup tables that ship with the package."""
from pathlib import Path

import pandas as pd

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"


def load_wmo_codes() -> pd.DataFrame:
    """Read wmo_codes.csv and return columns weather_code, weather_description, weather_category."""
    df = pd.read_csv(REFERENCE_DIR / "wmo_codes.csv")
    return df.rename(columns={
        "code": "weather_code",
        "description": "weather_description",
        "category": "weather_category",
    })

def load_weatherapi_codes() -> pd.DataFrame:
    """Read weatherapi_codes.csv and return columns weather_code, weather_description, weather_category."""
    df = pd.read_csv(REFERENCE_DIR / "weatherapi_codes.csv")
    return df.rename(columns={
        "code": "weather_code",
        "description": "weather_description",
        "category": "weather_category",
    })