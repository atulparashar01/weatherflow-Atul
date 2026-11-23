"""Force an error in the middle of a load and show that nothing is saved."""

from pathlib import Path

import pandas as pd
import psycopg

from weatherflow.config import load_config
from weatherflow.load import get_database_url, load

config = load_config()
paths = config["paths"]


def count_fact_rows():
    with psycopg.connect(get_database_url()) as conn:
        return conn.execute("SELECT COUNT(*) FROM fact_weather_hourly").fetchone()[0]


# 1. Take the data from the newest Parquet file
newest = sorted(Path(paths["processed_dir"]).glob("weather_hourly/*/*.parquet"))[-1]
df = pd.read_parquet(newest)

# 2. Make the rows NEW by moving every hour 30 days forward
df["observed_at_utc"] = df["observed_at_utc"] + pd.Timedelta(days=30)
df["observed_at_local"] = df["observed_at_local"] + pd.Timedelta(days=30)

# 3. Break the LAST row: "extreme" is not allowed by the CHECK
df.loc[df.index[-1], "outdoor_work_risk"] = "extreme"

before = count_fact_rows()
print("Fact rows BEFORE:", before)

try:
    load(df, config["cities"], config["dim_date"], paths["schema"])
except Exception as error:
    print("The load failed, as expected:", type(error).__name__)

after = count_fact_rows()
print("Fact rows AFTER: ", after)
print("Nothing was saved." if before == after else "PROBLEM: some rows were saved!")