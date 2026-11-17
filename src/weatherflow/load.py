"""Load step: write the clean table into SQLite."""
import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)
from datetime import datetime


def load(df: pd.DataFrame, db_path: Path, schema_path: Path) -> int:
    """Create the table if needed, write the rows and return how many were written."""
    out = df.copy()
    out["observed_at_utc"] = out["observed_at_utc"].map(pd.Timestamp.isoformat)
    out["observed_at_local"] = out["observed_at_local"].map(pd.Timestamp.isoformat)
    out = out.astype(object).where(out.notna(), None)          # missing -> NULL
    rows = list(out.itertuples(index=False, name=None))

    columns = list(out.columns)                   # the INSERT follows the table's columns
    insert = (f"INSERT OR REPLACE INTO weather_hourly ({', '.join(columns)}) "
              f"VALUES ({', '.join('?' * len(columns))})")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with conn:                                                  # saves if no error
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.executemany(insert, rows)
    conn.close()

    logger.info("Loaded %d rows into %s", len(rows), db_path)
    return len(rows)

def write_parquet(df: pd.DataFrame, processed_dir: Path, run_time: datetime) -> Path:
    """Write the table to <processed_dir>/weather_hourly/run_date=<date>/part-<timestamp>.parquet."""
    folder = processed_dir / "weather_hourly" / f"run_date={run_time:%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"part-{run_time:%Y%m%dT%H%M%S}.parquet"
    df.to_parquet(path, index=False)

    logger.info("Wrote %d rows to %s", len(df), path)
    return path