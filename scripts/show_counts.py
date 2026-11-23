"""Print how many rows are in each table, and how many per source."""

import psycopg

from weatherflow.load import get_database_url

with psycopg.connect(get_database_url()) as conn:
    for table in ["dim_city", "dim_date", "fact_weather_hourly"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")

    print("\nfact_weather_hourly per source:")
    rows = conn.execute(
        "SELECT source, COUNT(*) FROM fact_weather_hourly GROUP BY source ORDER BY source"
    ).fetchall()
    for source, count in rows:
        print(f"  {source}: {count}")