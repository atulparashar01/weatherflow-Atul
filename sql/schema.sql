-- WeatherFlow star schema (SQLite)
-- Grain of the fact table: one row per city, per hour, per source.
-- Safe to run many times: every table uses CREATE TABLE IF NOT EXISTS.

-- 1. Dimension: one row per city
CREATE TABLE IF NOT EXISTS dim_city (
    city_id    INTEGER PRIMARY KEY,          -- number made by the database
    city_name  TEXT    NOT NULL UNIQUE,      -- natural key, e.g. London
    country    TEXT    NOT NULL,
    latitude   REAL    NOT NULL,
    longitude  REAL    NOT NULL
);

-- 2. Dimension: one row per calendar day
CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INTEGER PRIMARY KEY,        -- YYYYMMDD, e.g. 20260701
    full_date    TEXT    NOT NULL UNIQUE,    -- 2026-07-01
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day          INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    day_of_week  TEXT    NOT NULL,           -- Monday ... Sunday
    is_weekend   INTEGER NOT NULL CHECK (is_weekend IN (0, 1))
);

-- 3. Fact: the weather measurements
CREATE TABLE IF NOT EXISTS fact_weather_hourly (
    city_id              INTEGER NOT NULL,
    date_id              INTEGER NOT NULL,   -- London (local) date
    observed_at_utc      TEXT    NOT NULL,   -- exact hour in UTC
    hour_local           INTEGER NOT NULL CHECK (hour_local BETWEEN 0 AND 23),
    source               TEXT    NOT NULL,   -- e.g. open-meteo

    temperature_c        REAL,
    temperature_f        REAL,
    feels_like_c         REAL,
    humidity_pct         INTEGER,
    precipitation_mm     REAL,
    wind_speed_kmh       REAL,
    wind_speed_ms        REAL,
    beaufort_scale       INTEGER,
    weather_code         INTEGER,
    weather_description  TEXT    NOT NULL,
    weather_category     TEXT    NOT NULL,
    is_daylight          INTEGER CHECK (is_daylight IN (0, 1)),
    outdoor_work_risk    TEXT    NOT NULL
                         CHECK (outdoor_work_risk IN ('low', 'medium', 'high')),
    ingested_at_utc      TEXT    NOT NULL,

    PRIMARY KEY (city_id, observed_at_utc, source),
    FOREIGN KEY (city_id) REFERENCES dim_city (city_id),
    FOREIGN KEY (date_id) REFERENCES dim_date (date_id)
);