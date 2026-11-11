# Data Dictionary: WeatherFlow hourly weather

| Item | Detail |
|---|---|
| **Source** | Open-Meteo Forecast API: <https://api.open-meteo.com/v1/forecast> |
| **Documentation** | <https://open-meteo.com/en/docs> |
| **Licence** | Open-Meteo data is available under CC BY 4.0, so attribution to Open-Meteo is required |
| **Refresh frequency** | The source provides hourly values. WeatherFlow plans to extract hourly (Airflow, Week 3). Until then `extract.py` is run manually |
| **Grain** | One row per city per hour |
| **Cities** | London, Manchester, Birmingham, Edinburgh, Cardiff |
| **Time zone** | `Europe/London` local time (set with the `timezone` request parameter) |
| **Request window** | `past_days=1` and `forecast_days=1`, so each response holds 48 hourly rows (yesterday and today) |

## Columns

| Column | Type | Unit | Description | Example | Nullable? | Source |
|---|---|---|---|---|---|---|
| `time` | datetime (local time, no time zone attached) | Europe/London local time | Start of the hourly period | `2026-11-10T14:00` | No | Open-Meteo `hourly.time` |
| `temperature_2m` | float | °C | Air temperature 2 m above ground | `8.4` | Yes | Open-Meteo `hourly.temperature_2m` |
| `relative_humidity_2m` | integer | % | Relative humidity 2 m above ground | `87` | Yes | Open-Meteo `hourly.relative_humidity_2m` |
| `apparent_temperature` | float | °C | "Feels like" temperature, which accounts for wind and humidity | `6.1` | Yes | Open-Meteo `hourly.apparent_temperature` |
| `precipitation` | float | mm | Total rain, showers and snow (as water) over the preceding hour | `0.2` | Yes | Open-Meteo `hourly.precipitation` |
| `wind_speed_10m` | float | km/h | Wind speed 10 m above ground | `14.8` | Yes | Open-Meteo `hourly.wind_speed_10m` |
| `weather_code` | integer | WMO code | Weather condition as a WMO weather interpretation code (0 = clear sky, 3 = overcast, 61 = slight rain, 95 = thunderstorm). Needs a lookup table to read | `3` | Yes | Open-Meteo `hourly.weather_code` |
| `city` | string | n/a | City the row belongs to. The API response does not contain it, so it is added by `flatten()` from the raw file name | `London` | No | Added by WeatherFlow |
| `latitude` | float | degrees | Latitude of the grid point the API used. May differ slightly from the latitude requested | `51.5` | No | Open-Meteo top-level `latitude` |
| `longitude` | float | degrees | Longitude of the grid point the API used. May differ slightly from the longitude requested | `-0.12` | No | Open-Meteo top-level `longitude` |
| `source_file` | string | n/a | Name of the raw JSON file the row came from (lineage) | `london_20261110T062133.json` | No | Added by the notebook loader |

## Notes

- **Units** come from the `hourly_units` block of each API response. They are not stored in the column names.
- **Nullable:** the API can return `null` for a measurement, so every weather measurement column is nullable. `time`, `city`, `latitude`, `longitude` and `source_file` are always present.
- **Past and forecast rows:** each response mixes hours that have already happened with forecast hours. Forecast values can change on the next run.
- **Duplicates:** the same `(city, time)` can appear in more than one raw file. Removing them (keeping the latest) is planned for Task 1.5.
- **Weather codes:** the lookup table (code → description) is in `notebooks/01_explore.ipynb` and should be checked against the Open-Meteo documentation.