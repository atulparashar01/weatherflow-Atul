CREATE TABLE IF NOT EXISTS weather_hourly (
    city                TEXT NOT NULL,
    observed_at_utc     TEXT NOT NULL,
    observed_at_local   TEXT NOT NULL,
    temperature_c       REAL,
    feels_like_c        REAL,
    humidity_pct        INTEGER,
    precipitation_mm    REAL,
    wind_speed_kmh      REAL,
    weather_code        INTEGER,
    weather_description TEXT,
    weather_category    TEXT,
    ingested_at_utc     TEXT NOT NULL,
    PRIMARY KEY (city, observed_at_utc)
);