"""Command-line entry point:  python -m weatherflow run"""
import argparse
import logging
import sys

from weatherflow.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weatherflow", description="WeatherFlow weather data pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="run the pipeline")
    # more sub-commands come later, for example:
    # subparsers.add_parser("backfill", help="load historical data")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.command == "run":
        return run_pipeline()
    return 1


if __name__ == "__main__":
    sys.exit(main())