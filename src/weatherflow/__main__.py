"""Command-line entry point:  python -m weatherflow run   or   python -m weatherflow backfill"""
import argparse
import logging
import sys
from datetime import date

from weatherflow.pipeline import run_backfill, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser with its sub-commands."""
    parser = argparse.ArgumentParser(
        prog="weatherflow", description="WeatherFlow weather data pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="run the pipeline")

    backfill = subparsers.add_parser("backfill", help="load history from the archive API")
    backfill.add_argument("--days", type=int, default=30,
                          help="number of days, ending 5 days ago (default 30)")
    backfill.add_argument("--start-date", type=date.fromisoformat, help="first day, YYYY-MM-DD")
    backfill.add_argument("--end-date", type=date.fromisoformat, help="last day, YYYY-MM-DD")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Read the command, set up logging once and run it. Return the exit code."""
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.command == "run":
        return run_pipeline()
    if args.command == "backfill":
        return run_backfill(args.days, args.start_date, args.end_date)
    return 1


if __name__ == "__main__":
    sys.exit(main())