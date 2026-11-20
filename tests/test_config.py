"""Tests for config.py. A small config file is written to a temporary folder."""

import pytest

from weatherflow import config as config_module

GOOD_CONFIG = """
api: {forecast_url: "http://example.invalid", timeout_seconds: 5, max_retries: 3, hourly_variables: [temperature_2m], timezone: UTC}
cities:
  - {name: London, latitude: 51.5, longitude: -0.12}
paths: {raw_dir: data/raw, database: data/weather.db, schema: sql/schema.sql}
"""


def use_config(monkeypatch, tmp_path, text):
    """Point load_config() at a config file written in tmp_path."""
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_FILE", path)


def test_paths_in_the_config_are_made_absolute(monkeypatch, tmp_path):
    use_config(monkeypatch, tmp_path, GOOD_CONFIG)

    config = config_module.load_config()

    assert config["paths"]["raw_dir"] == (tmp_path / "data" / "raw").resolve()
    assert config["paths"]["raw_dir"].is_absolute()


def test_missing_section_is_reported_by_name(monkeypatch, tmp_path):
    use_config(monkeypatch, tmp_path, GOOD_CONFIG.replace("cities:", "towns:"))

    with pytest.raises(ValueError, match="cities"):
        config_module.load_config()


def test_missing_api_key_is_reported_by_name(monkeypatch, tmp_path):
    use_config(monkeypatch, tmp_path, GOOD_CONFIG.replace("max_retries: 3, ", ""))

    with pytest.raises(ValueError, match="max_retries"):
        config_module.load_config()