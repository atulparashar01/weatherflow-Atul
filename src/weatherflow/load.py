"""Load the cleaned data into SQLite (star schema) and into Parquet files."""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SOURCE = "open_meteo_forecast"


class DatabaseUrlError(RuntimeError):
    """DATABASE_URL is not set."""


def get_database_url() -> str:
    """Read DATABASE_URL from .env or the environment. It holds the password, so never log it."""
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise DatabaseUrlError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    return url

# Columns of fact_weather_hourly, in the order we insert them.
FACT_COLUMNS = [
    "city_id", "date_id", "observed_at_utc", "hour_local", "source",
    "temperature_c", "temperature_f", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "wind_speed_ms", "beaufort_scale",
    "weather_code", "weather_description", "weather_category",
    "is_daylight", "outdoor_work_risk", "ingested_at_utc",
]

# These three columns together are the primary key.
KEY_COLUMNS = ["city_id", "observed_at_utc", "source"]


def build_dim_date(start, end) -> pd.DataFrame:
    """Return one row per day from start to end (both included)."""
    days = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "date_id": days.strftime("%Y%m%d").astype(int),
            "full_date": days.strftime("%Y-%m-%d"),
            "year": days.year,
            "month": days.month,
            "day": days.day,
            "day_of_week": days.day_name(),
            "is_weekend": days.dayofweek >= 5,          # True or False (BOOLEAN)
        }
    )


def load_dim_date(conn, dim_date_range) -> None:
    """Save every day in dim_date. Days never change, so existing ones are skipped."""
    days = build_dim_date(dim_date_range["start"], dim_date_range["end"])
    with conn.cursor() as cur:                         # executemany belongs to a cursor, not the connection
        cur.executemany(
            """
            INSERT INTO dim_date
                (date_id, full_date, year, month, day, day_of_week, is_weekend)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_id) DO NOTHING
            """,
            days.astype(object).values.tolist(),
        )


def load_dim_city(conn, cities):
    """Save every city in dim_city. Return {city_name: city_id}."""

    sql = """
        INSERT INTO dim_city (city_name, country, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (city_name) DO UPDATE SET
            country   = EXCLUDED.country,
            latitude  = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
    """

    # Part 1: save each city
    for city in cities:
        conn.execute(sql, (city["name"], city["country"],
                           city["latitude"], city["longitude"]))

    # Part 2: read the ids back
    city_ids = {}
    for name, city_id in conn.execute("SELECT city_name, city_id FROM dim_city"):
        city_ids[name] = city_id

    return city_ids


def get_high_water_mark(conn, city_name: str, source: str, now_utc: datetime):
    """Latest hour already loaded for a city and source, ignoring hours still in the future.

    Returns a UTC Timestamp, or None if nothing has been loaded yet.
    """
    row = conn.execute(
        """
        SELECT MAX(f.observed_at_utc)
        FROM fact_weather_hourly AS f
        JOIN dim_city AS c ON c.city_id = f.city_id
        WHERE c.city_name = %s AND f.source = %s AND f.observed_at_utc <= %s
        """,
        (city_name, source, now_utc),
    ).fetchone()
    return pd.Timestamp(row[0]) if row[0] else None


def build_fact_rows(df: pd.DataFrame, city_ids: dict, source: str) -> list:
    """Turn the cleaned DataFrame into a list of rows for fact_weather_hourly."""
    data = df.copy()

    data["city_id"] = data["city"].map(city_ids)      # London -> 1
    data["source"] = source

    # London (local) date and hour, taken from observed_at_local
    data["date_id"] = data["observed_at_local"].dt.strftime("%Y%m%d").astype(int)
    data["hour_local"] = data["observed_at_local"].dt.hour

    # TIMESTAMPTZ stores an instant: give it timezone-aware UTC datetimes
    for col in ["observed_at_utc", "ingested_at_utc"]:
        data[col] = [t.to_pydatetime() for t in pd.to_datetime(data[col], utc=True)]

    data = data[FACT_COLUMNS].astype(object)
    data = data.where(data.notna(), None)              # missing value -> NULL
    return data.values.tolist()


def upsert_facts(conn, rows) -> int:
    """Insert or update the fact rows. Return how many were NEW (the rest were updated)."""
    if not rows:
        return 0
    update_cols = [c for c in FACT_COLUMNS if c not in KEY_COLUMNS]
    sql = f"""
        INSERT INTO fact_weather_hourly ({", ".join(FACT_COLUMNS)})
        VALUES ({", ".join("%s" for _ in FACT_COLUMNS)})
        ON CONFLICT ({", ".join(KEY_COLUMNS)}) DO UPDATE SET
            {", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)}
        RETURNING (xmax = 0) AS inserted
    """
    new_rows = 0
    with conn.cursor() as cur:
        cur.executemany(sql, rows, returning=True)
        while True:
            if cur.fetchone()[0]:              # xmax = 0 means the row is new
                new_rows += 1
            if not cur.nextset():
                break
    return new_rows


def load(df, cities, dim_date_range, schema_path, source=SOURCE) -> int:
    """Load dim_city, dim_date and fact_weather_hourly in ONE transaction.

    If anything fails, nothing is saved. Returns the number of fact rows.
    """
    with psycopg.connect(get_database_url()) as conn:
        with conn.transaction():                       # commit if OK, rollback if error
            conn.execute(Path(schema_path).read_text(encoding="utf-8"))
            load_dim_date(conn, dim_date_range)
            city_ids = load_dim_city(conn, cities)
            rows = build_fact_rows(df, city_ids, source)
            new_rows = upsert_facts(conn, rows)

    logger.info("Loaded %d rows into fact_weather_hourly (%d new, %d updated)",
                len(rows), new_rows, len(rows) - new_rows)
    return len(rows)


def read_source_rows(source: str, first_hour, last_hour) -> pd.DataFrame:
    """Read city, hour and temperature of one source between two hours (for the cross-source check)."""
    columns = ["city", "observed_at_utc", "temperature_c"]
    try:
        with psycopg.connect(get_database_url()) as conn:
            rows = conn.execute(
                """
                SELECT c.city_name, f.observed_at_utc, f.temperature_c
                FROM fact_weather_hourly AS f
                JOIN dim_city AS c ON c.city_id = f.city_id
                WHERE f.source = %s AND f.observed_at_utc BETWEEN %s AND %s
                """,
                (source, pd.Timestamp(first_hour).to_pydatetime(), pd.Timestamp(last_hour).to_pydatetime()),
            ).fetchall()
    except psycopg.errors.UndefinedTable:              # the tables do not exist yet
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def write_parquet(df: pd.DataFrame, processed_dir, run_time: datetime, source: str = "") -> Path:
    """Save the data as a Parquet file inside a run_date=YYYY-MM-DD folder."""
    folder = Path(processed_dir) / "weather_hourly" / f"run_date={run_time:%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    tag = f"_{source}" if source else ""
    path = folder / f"part-{run_time:%Y%m%dT%H%M%S}{tag}.parquet"
    df.to_parquet(path, index=False)
    logger.info("Wrote %s", path)
    return path