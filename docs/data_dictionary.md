# Data Dictionary: weather_hourly

- **Source:** Open-Meteo Forecast API (<https://api.open-meteo.com/v1/forecast>), licence CC BY 4.0 (attribution required)
- **Grain:** one row per city per hour
- **Primary key:** (city, observed_at_utc)
- **Timezone:** `observed_at_utc` is UTC; `observed_at_local` is Europe/London
- **Cities:** London, Manchester, Birmingham, Edinburgh, Cardiff
- **Refresh:** run with `python -m weatherflow run`. Each run loads 48 hours per city (yesterday and today)

## Columns

| Column | Type | Unit | Description | Example | Nullable | Source field |
|---|---|---|---|---|---|---|
| city | TEXT | - | City name | London | No | `cities` in config.yaml |
| observed_at_utc | TEXT (ISO 8601) | UTC | Start of the hour, in UTC | 2026-11-12T14:00:00+00:00 | No | `hourly.time` |
| observed_at_local | TEXT (ISO 8601) | Europe/London | Same hour in London time (+00:00 in winter, +01:00 in summer) | 2026-07-01T15:00:00+01:00 | No | Derived: `observed_at_utc` converted to Europe/London |
| temperature_c | REAL | °C | Air temperature 2 m above ground | 8.4 | Yes | `hourly.temperature_2m` |
| temperature_f | REAL | °F | Air temperature in Fahrenheit. Formula: `temperature_c * 9/5 + 32` | 47.1 | Yes | Derived |
| feels_like_c | REAL | °C | "Feels like" temperature (wind and humidity included) | 6.1 | Yes | `hourly.apparent_temperature` |
| humidity_pct | INTEGER | % | Relative humidity 2 m above ground | 87 | Yes | `hourly.relative_humidity_2m` |
| precipitation_mm | REAL | mm | Rain, showers and snow (as water) in the preceding hour | 0.2 | Yes | `hourly.precipitation` |
| wind_speed_kmh | REAL | km/h | Wind speed 10 m above ground | 14.8 | Yes | `hourly.wind_speed_10m` |
| wind_speed_ms | REAL | m/s | Wind speed in metres per second. Formula: `wind_speed_kmh / 3.6` | 4.11 | Yes | Derived |
| beaufort_scale | INTEGER | 0 to 12 | Beaufort force for `wind_speed_ms`, using the limits below | 3 | Yes | Derived |
| weather_code | INTEGER | WMO code | Weather condition code (0 = clear sky, 3 = overcast, 63 = moderate rain, 95 = thunderstorm) | 3 | Yes | `hourly.weather_code` |
| weather_description | TEXT | - | Text for the WMO code. `unknown` if the code is missing or not in the lookup | Overcast | No | `wmo_codes.csv` |
| weather_category | TEXT | - | One of: clear, cloudy, fog, drizzle, rain, snow, storm, unknown | cloudy | No | `wmo_codes.csv` |
| is_daylight | INTEGER | 1 or 0 | 1 = daylight, 0 = night | 1 | Yes | `hourly.is_day` |
| outdoor_work_risk | TEXT | - | Risk to outdoor work: `high`, `medium` or `low`. Rules below | low | No | Derived |
| ingested_at_utc | TEXT (ISO 8601) | UTC | When the pipeline loaded this row | 2026-11-17T12:16:15+00:00 | No | Added by `transform()` |

## Derived metrics

| Column | Rule |
|---|---|
| temperature_f | `temperature_c * 9/5 + 32` |
| wind_speed_ms | `wind_speed_kmh / 3.6` |
| beaufort_scale | The force whose lower limit is at or below `wind_speed_ms` (table below) |
| is_daylight | Taken from the API's `is_day` (1 = daylight, 0 = night) |
| outdoor_work_risk | See the risk rules below |

### Beaufort limits

| Force | From (m/s) | Force | From (m/s) |
|---|---|---|---|
| 0 | 0 | 7 | 13.9 |
| 1 | 0.5 | 8 | 17.2 |
| 2 | 1.6 | 9 | 20.8 |
| 3 | 3.4 | 10 | 24.5 |
| 4 | 5.5 | 11 | 28.5 |
| 5 | 8.0 | 12 | 32.7 |
| 6 | 10.8 | | |

A wind speed belongs to the highest force whose "From" value it reaches. For example, 8.0 m/s is force 5, and 40 m/s is force 12.

### Outdoor work risk rules

| Level | When |
|---|---|
| **high** | Beaufort ≥ 7, **or** `weather_category` is storm or snow, **or** `precipitation_mm` ≥ 4 |
| **medium** | Not high, and (Beaufort ≥ 5, **or** `precipitation_mm` ≥ 1, **or** `temperature_c` ≤ 0) |
| **low** | Everything else |

## Notes

- Measurement columns can be NULL because the API sometimes returns no value.
- If the inputs to a rule are missing, that rule does not match. An hour with no wind, rain or temperature data therefore shows `low`.
- Each run mixes past hours with forecast hours, so re-running replaces earlier values for the same (city, hour).
- `INSERT OR REPLACE` on the primary key means running the pipeline twice does not create duplicates.
