"""Wires the steps together: extract -> transform -> load."""
import logging

from weatherflow.config import load_config
from weatherflow.extract import extract_all
from weatherflow.load import load
from weatherflow.transform import transform

logger = logging.getLogger(__name__)


def run_pipeline() -> int:
    """Run the whole pipeline. Return 0 if every city worked, 1 if any city failed."""
    config = load_config()
    paths = config["paths"]
    logger.info("Pipeline started")

    raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"])
    if raw:                                          # load the cities that worked
        load(transform(raw), paths["database"], paths["schema"])

    if failed:                                       # then fail loudly
        logger.error("Run FAILED: no data for %s", ", ".join(failed))
        return 1
    logger.info("Run succeeded")
    return 0