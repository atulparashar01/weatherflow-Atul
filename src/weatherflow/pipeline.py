"""Wires the steps together: extract -> transform -> load."""
import logging
from datetime import datetime, timezone

from weatherflow.config import load_config
from weatherflow.extract import extract_all
from weatherflow.load import load, write_parquet
from weatherflow.reference import load_wmo_codes
from weatherflow.transform import transform

logger = logging.getLogger(__name__)


def run_pipeline() -> int:
    """Run the whole pipeline. Return 0 if every city worked, 1 if any city failed."""
    config = load_config()
    paths = config["paths"]
    logger.info("Pipeline started")

    raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"])
    if raw:                                          # load the cities that worked
        df = transform(raw, load_wmo_codes())
        load(df, paths["database"], paths["schema"])
        write_parquet(df, paths["processed_dir"], datetime.now(timezone.utc))

    if failed:                                       # then fail loudly
        logger.error("Run FAILED: no data for %s", ", ".join(failed))
        return 1
    logger.info("Run succeeded")
    return 0