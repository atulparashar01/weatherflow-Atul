"""Compare the size of the same data saved as CSV and as Parquet."""
import pandas as pd

from weatherflow.config import load_config

processed_dir = load_config()["paths"]["processed_dir"]
folder = processed_dir / "weather_hourly"

# 1. Read every Parquet file and join them into one table
files = list(folder.rglob("*.parquet"))
tables = [pd.read_parquet(f) for f in files]
df = pd.concat(tables)

# 2. Remove repeated hours, so both formats hold exactly the same rows
df = df.drop_duplicates(subset=["city", "observed_at_utc"])

# 3. Save the same table in both formats (in a separate folder)
out = processed_dir / "size_test"
out.mkdir(exist_ok=True)
df.to_csv(out / "weather.csv", index=False)
df.to_parquet(out / "weather.parquet", index=False)

# 4. Compare the file sizes
csv_kb = (out / "weather.csv").stat().st_size / 1024
parquet_kb = (out / "weather.parquet").stat().st_size / 1024

print("Parquet files read:", len(files))
print("Rows:", len(df))
print(f"CSV:     {csv_kb:.1f} KB")
print(f"Parquet: {parquet_kb:.1f} KB")
print(f"CSV is {csv_kb / parquet_kb:.1f} times bigger than Parquet")