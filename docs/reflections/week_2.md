# Week 2 Reflection: Modular Pipeline, Star Schema, Data Quality and Tests

**Name:** Atul Parashar
**Week:** 2 (Thu 12 Nov to Wed 18 Nov 2026)
**Repo:** https://github.com/atulparashar01/weatherflow-Atul

> Draft. Copy these sections into the programme's reflection template if its headings differ, and replace anything in [square brackets] with your own details.

## What I built

| Task | Deliverable | Status |
|---|---|---|
| 2.1 Package, config, logging, CLI | `src/weatherflow/` package, `config.yaml`, logging, `python -m weatherflow run` | Done |
| 2.2 Transformations and Parquet | `transform.py` (units, weather descriptions, Beaufort scale, `outdoor_work_risk`), Parquet output partitioned by run date | Done |
| 2.3 Star schema and idempotent load | `sql/schema.sql`, `docs/erd.md`, `load.py` (upserts in one transaction), `sql/analysis_queries.sql`, `scripts/show_counts.py`, `scripts/force_error.py` | Done |
| 2.4 Data quality and quarantine | `validate.py` (8 checks), quarantine files, DQ reports in `docs/dq_reports/`, `scripts/inject_bad_data.py` | Done |
| 2.5 Testing with pytest | 36 tests, fixtures, mocked API, coverage report (72%) | Done |
| 2.6 Backfill and incremental load | `python -m weatherflow backfill`, high-water mark, 2-hour overlap, watermark tests | Done (merged without a peer review, see below) |

## What I learned

- **A star schema starts with the grain.** One row per city, per hour, per source decides the primary key `(city_id, observed_at_utc, source)`. Dimensions hold names and dates, the fact table holds measurements.
- **Idempotency needs three things together.** A primary key, an upsert (`INSERT ... ON CONFLICT DO UPDATE`) and one transaction. Running the pipeline three times gave 240 fact rows every time, and a forced error in the middle of a load saved nothing.
- **Bad data needs a plan, not a crash.** Bad rows are quarantined with a reason, serious problems (duplicates, missing hours) stop the run, and soft problems only warn. Every run writes a report.
- **Tests should be small and aimed.** Mock the API so tests run offline, use `tmp_path` for files and `parametrize` for boundary cases such as exactly 4 mm of rain.
- **Backfill and incremental loads share one code path.** The high-water mark (latest past hour already loaded) says where to start, and a 2-hour overlap catches late corrections. Because the load is an upsert, the overlap does not create duplicates.
- **Coverage only counts what it can see.** Without `__init__.py` three modules were left out of the report, so the 80% figure was not real.

## What was hard

- **The coverage number was wrong.** My first report said 80%. The mentor pointed out that `src/weatherflow/__init__.py` was missing, so `pipeline.py`, `config.py` and `__main__.py` were not measured. With them included the real total is 72%, and `pipeline.py` is only 21%.
- **A commit message promised files that were not in the commit.** It said `analysis_queries.sql` and two proof scripts were added, but they were never staged. I did not read `git status` carefully. I now read it before every commit.
- **Old files kept coming back.** Several errors (a `TypeError` in `load()`, a missing `is_day` column, a missing `fetch_city_range`) came from having an old copy of a file next to new code. I now check that each file really changed before I run the pipeline.
- **OneDrive and Git.** Git sometimes asks "Deletion of directory failed" inside OneDrive. I answer `n`.
- **No review partner for Task 2.6.** I merged the backfill PR without a second person reviewing it.
- [Add anything else that was hard for you.]

## What went well

- Every Week 1 fix was applied as one commit per fix.
- The load runs in one transaction, and a failed city gives exit code 1.
- The backfill loaded 3600 rows and loaded the same 3600 again with no change in row counts.
- The README is honest about which modules are weakly tested.

## What I would do differently

- Read `git status` before every commit, and check the commit message against the files in it.
- Add `__init__.py` when I create the package, so coverage is honest from the start.
- Write the tests for `pipeline.py` (it is at 21%) instead of leaving it to manual runs.
- Ask for a review partner on day one of a task that needs one.

## Evidence

- Idempotency: 240 fact rows after run 1, run 2 and run 3.
- Atomic load: `python scripts/force_error.py` prints the failure and "Nothing was saved."
- Data quality: `python scripts/inject_bad_data.py` quarantines a 99 °C reading and stops the run on a duplicate row.
- Tests: `python -m pytest -v --cov=src --cov-report=term-missing` gives 36 passed, TOTAL 72%.
- Backfill: 3600 rows loaded, unchanged after a second run.
- SQL: `sql/analysis_queries.sql` has 5 queries, all using joins on the star schema.
- Documents: `docs/erd.md`, `docs/dq_reports/`.

## Skills practised

Python packaging and a command-line interface, YAML configuration, logging, pandas transformations, Parquet, star schema design, SQLite and SQL joins, upserts and transactions, data quality checks and quarantine, pytest (fixtures, parametrize, mocks, coverage), incremental loading with a high-water mark, backfill, Git workflow with branches and PRs.

## Goals for Week 3

- [Replace with the Week 3 goals from the programme.]
- Raise `pipeline.py` test coverage.
- Get a peer review on my next PR.

## Questions I still have

- [Add one or two, for example how to schedule the pipeline every hour, or how to test a function that calls several others.]
