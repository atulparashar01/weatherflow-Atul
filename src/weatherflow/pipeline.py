"""Wires the steps together: extract -> transform -> validate -> load."""
import logging
from datetime import datetime, timezone

from weatherflow.config import load_config
from weatherflow.extract import extract_all
from weatherflow.load import load, write_parquet
from weatherflow.reference import load_wmo_codes
from weatherflow.transform import transform
from weatherflow.validate import (
    DataQualityError,
    raise_if_blocking_failures,
    validate,
    write_dq_report,
    write_quarantine,
)

logger = logging.getLogger(__name__)


def run_pipeline() -> int:
    """Run the whole pipeline. Return 0 if everything worked, 1 if not."""
    config = load_config()
    paths = config["paths"]
    run_time = datetime.now(timezone.utc)
    logger.info("Pipeline started")

    raw, failed = extract_all(config["cities"], config["api"], paths["raw_dir"])
    if raw:
        df = transform(raw, load_wmo_codes())

        # Validate: split good and bad rows, then save the evidence
        good, quarantined, results = validate(df, config)
        write_quarantine(quarantined, paths["quarantine_dir"], run_time)
        write_dq_report(results, good, quarantined, paths["dq_reports_dir"], run_time)

        # Stop before loading if a blocking check failed
        try:
            raise_if_blocking_failures(results)
        except DataQualityError as error:
            logger.error("Run FAILED: %s", error)
            return 1

        load(good, config["cities"], config["dim_date"], paths["database"], paths["schema"])
        write_parquet(good, paths["processed_dir"], run_time)

    if failed:
        logger.error("Run FAILED: no data for %s", ", ".join(failed))
        return 1
    logger.info("Run succeeded")
    return 0