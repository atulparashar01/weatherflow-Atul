# Data Dictionary: weather_hourly

- **Source:** Open-Meteo Forecast API (<https://api.open-meteo.com/v1/forecast>), licence CC BY 4.0 (attribution required)
- **Grain:** one row per city per hour
- **Primary key:** (city, observed_at_utc)
- **Timezone:** `observed_at_utc` is UTC; `observed_at_local` is Europe/London
- **Cities:** London, Manchester, Birmingham, Edinburgh, Cardiff
- **Refresh:** run manually with `python etl_v1.py`. Each run loads 48 hours per city (yesterday and today)

| Column | Type | Unit | Description | Example | Nullable | Source field |
|---|---|---|---|---|---|---|
| city | TEXT | - | City name | London | No | `CITIES` in extract.py |
| observed_at_utc | TEXT (ISO 8601) | UTC | Start of the hour, in UTC | 2026-11-12T14:00:00+00:00 | No | `hourly.time` |
| observed_at_local | TEXT (ISO 8601) | Europe/London | Same hour in London time (+00:00 in winter, +01:00 in summer) | 2026-07-01T15:00:00+01:00 | No | Converted from `hourly.time` |
| temperature_c | REAL | °C | Air temperature 2 m above ground | 8.4 | Yes | `hourly.temperature_2m` |
| feels_like_c | REAL | °C | "Feels like" temperature (wind and humidity included) | 6.1 | Yes | `hourly.apparent_temperature` |
| humidity_pct | INTEGER | % | Relative humidity 2 m above ground | 87 | Yes | `hourly.relative_humidity_2m` |
| precipitation_mm | REAL | mm | Rain, showers and snow (as water) in the preceding hour | 0.2 | Yes | `hourly.precipitation` |
| wind_speed_kmh | REAL | km/h | Wind speed 10 m above ground | 14.8 | Yes | `hourly.wind_speed_10m` |
| weather_code | INTEGER | WMO code | Weather condition code (0 = clear, 3 = overcast, 61 = slight rain, 95 = thunderstorm) | 3 | Yes | `hourly.weather_code` |
| ingested_at_utc | TEXT (ISO 8601) | UTC | When the pipeline loaded this row | 2026-11-14T12:29:33+00:00 | No | Added by `transform()` in etl_v1.py |

## Notes

- Measurement columns can be NULL because the API sometimes returns no value.
- Each run mixes past hours with forecast hours, so re-running replaces earlier values for the same (city, hour).
- `INSERT OR REPLACE` on the primary key means running the pipeline twice does not create duplicates.