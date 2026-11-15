"""Load config.yaml and check that nothing important is missing."""
from pathlib import Path

import yaml

# src/weatherflow/config.py -> parents[2] is the project root
CONFIG_FILE = Path(__file__).resolve().parents[2] / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. Check the sections exist
    for section in ["api", "cities", "paths"]:
        if section not in config:
            raise ValueError(f"config.yaml: missing '{section}'")

    # 2. Check the keys we need inside api and paths
    for key in ["forecast_url", "timeout_seconds", "max_retries", "hourly_variables", "timezone"]:
        if key not in config["api"]:
            raise ValueError(f"config.yaml: missing '{key}' under 'api'")
    for key in ["raw_dir", "database"]:
        if key not in config["paths"]:
            raise ValueError(f"config.yaml: missing '{key}' under 'paths'")

    # 3. Turn every path into a full path, starting from the project folder
    root = CONFIG_FILE.parent
    for key, value in config["paths"].items():
        config["paths"][key] = (root / value).resolve()

    return config