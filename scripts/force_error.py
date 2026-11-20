"""Force an error in the middle of a load and show that nothing is saved."""

import sqlite3
from pathlib import Path

import pandas as pd

from weatherflow.config import load_config
from weatherflow.load import load

config = load_config()
paths = config["paths"]


def count_fact_rows():
    conn = sqlite3.connect(paths["database"])
    count = conn.execute("SELECT COUNT(*) FROM fact_weather_hourly").fetchone()[0]
    conn.close()
    return count


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
    load(df, config["cities"], config["dim_date"], paths["database"], paths["schema"])
except Exception as error:
    print("The load failed, as expected:", error)

after = count_fact_rows()
print("Fact rows AFTER: ", after)
print("Nothing was saved." if before == after else "PROBLEM: some rows were saved!")