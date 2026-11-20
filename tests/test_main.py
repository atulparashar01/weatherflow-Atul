"""Tests for the command line (__main__.py). The pipeline itself is replaced by a fake."""

from datetime import date

from weatherflow.__main__ import main


def test_main_run_returns_0_when_the_pipeline_succeeds(monkeypatch):
    monkeypatch.setattr("weatherflow.__main__.run_pipeline", lambda: 0)

    assert main(["run"]) == 0


def test_main_run_returns_1_when_the_pipeline_fails(monkeypatch):
    monkeypatch.setattr("weatherflow.__main__.run_pipeline", lambda: 1)

    assert main(["run"]) == 1


def test_main_backfill_passes_its_dates_to_the_pipeline(monkeypatch):
    received = {}

    def fake_backfill(days, start_date, end_date):
        received.update(days=days, start_date=start_date, end_date=end_date)
        return 0

    monkeypatch.setattr("weatherflow.__main__.run_backfill", fake_backfill)

    status = main(["backfill", "--days", "10", "--start-date", "2026-10-01", "--end-date", "2026-10-10"])

    assert status == 0
    assert received == {"days": 10, "start_date": date(2026, 10, 1), "end_date": date(2026, 10, 10)}