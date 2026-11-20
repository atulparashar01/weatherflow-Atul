"""Print how many rows are in each table."""

import sqlite3

from weatherflow.config import load_config

config = load_config()
conn = sqlite3.connect(config["paths"]["database"])

for table in ["dim_city", "dim_date", "fact_weather_hourly"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")

conn.close()