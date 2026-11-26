# Week 3 Reflection: Warehouse, Containers and Orchestration

**Name:** Atul Parashar
**Week:** 3 (Thu 19 Nov to Wed 25 Nov 2026)
**Repo:** https://github.com/atulparashar01/weatherflow-Atul

> Draft. Copy these sections into the programme's reflection template if its headings differ.

## What I built

| Task | Deliverable | Status |
|---|---|---|
| 3.1 Second source and secrets | WeatherAPI.com loaded through the same transform, validate and load path (`source = weatherapi_forecast`), key only in `.env`, clear error and exit code 1 when it is missing, cross-source temperature check (warning) with its threshold in `config.yaml`, ADR 001 | Done |
| 3.2 PostgreSQL warehouse | `postgres:18` in Docker Compose (named volume, health check, port 5433), `sql/schema_postgres.sql`, psycopg 3 upsert in one transaction, analysis queries on PostgreSQL | Done |
| 3.3 Containers | `Dockerfile` (non-root user, `ENTRYPOINT python -m weatherflow`), `.dockerignore`, a `pipeline` service in Compose, exit code passed through | Done |
| 3.4 Airflow | Airflow 3.4.0 in `orchestration/`, DAG `weatherflow_hourly`, shared Docker network (ADR 002) | Done |
| 3.5 CI with GitHub Actions | | Not done (optional) |
| 3.6 Dashboard, alerts, ADRs | ADR 003 (WeatherAPI time handling) written; dashboard and alert channel not built | Partly done (optional) |

## What I learned

- **Secrets stay out of everything.** The WeatherAPI key lives only in `.env`. I never log a URL (only the error type and status), and I searched the code, logs and Git for the first characters of the real key to prove it.
- **An upsert makes a load safe to repeat.** With the primary key `(city_id, observed_at_utc, source)` and `INSERT ... ON CONFLICT DO UPDATE`, three runs gave identical counts, and the load log says how many rows were new and how many were updated.
- **One transaction means all or nothing.** A forced error in the middle of a load saved no rows at all.
- **A container behaves the same everywhere.** The image has no `.env` inside it, runs as a non-root user, and passes the pipeline's exit code through, so a failed run is a failed container.
- **An orchestrator keeps its own state, not my data.** Airflow's database holds only run history. The weather data stays in the warehouse, and the two share a Docker network I chose and wrote down in ADR 002.
- **Time zones need proof, not a guess.** WeatherAPI does not say which timezone its `time` field uses, so I used `time_epoch` as UTC and checked it against `time` and the response's timezone (ADR 003).
- **`catchup=False` matters.** My laptop restarted overnight. Airflow skipped the missed hours instead of starting dozens of runs at once.

## What was hard

- **Windows and Git Bash details.** A folder named `.env` instead of a file, the `python` command opening the Microsoft Store, and Git Bash rewriting `/opt/...` paths inside Docker commands. Each one looked like a bug in my code until I read the error carefully.
- **Two passwords that did not match.** The database refused my login because `POSTGRES_PASSWORD` and the password inside `DATABASE_URL` in `.env` were different. I fixed it by making `DATABASE_URL` come from the same value.
- **Building the Airflow image.** `pip` failed twice inside the image: first because the copied files belonged to root, then because a leftover `egg-info` folder from my laptop was copied in. Setting the owner on the copy and ignoring `*.egg-info` fixed it.
- **Writing to the wrong file.** I once appended a wrong `DATABASE_URL` to the end of my real `.env`, because I ran a command from the wrong folder. I noticed because the second value was empty, removed that one line, and learned to run `pwd` first.
- **Proving a negative.** My first search for the key used an empty value and matched every file. I learned to check that the search text has the right length before trusting an empty result.

## What went well

- The whole chain runs: two APIs, validation, PostgreSQL, a container, and an hourly Airflow schedule.
- I tested the failure paths on purpose: a missing key, a mid-load error, a wrong key in Airflow (3 attempts, then an `ALERT:` line in the log), and re-running a past hour without changing the counts.
- 49 automated tests pass with 74% coverage, and the tests never call the real API.

## What I would do differently

- Start the optional tasks earlier, so CI and the dashboard are done before the deadline instead of left out.
- Run `pwd` and `git status` before every command that changes a file.
- Keep my Airflow laptop awake and plugged in during the scheduled runs, or run Airflow somewhere that does not restart.
- Write each ADR on the day I make the decision.

## Evidence

- WeatherAPI missing key: log line `Run FAILED: WEATHERAPI_KEY is not set`, exit code 1.
- PostgreSQL: three runs gave the same counts (360 rows); after a 30-day backfill the warehouse held 3,960 rows.
- Airflow: 7 successful scheduled hourly runs. A deliberate wrong key gave 3 attempts (the first try and 2 retries) and then `ALERT: task run_weatherapi of DAG weatherflow_hourly failed (... try 3)`.
- Re-running the 08:00 run left the counts unchanged: 3,600 archive, 480 `open_meteo_forecast`, 360 `weatherapi_forecast`.
- Tests: 49 passed, TOTAL coverage 74%.
- Decisions: `docs/adr/001`, `002` and `003`.

## Skills practised

Secrets handling with `.env`, a second API and source reconciliation, PostgreSQL and psycopg 3, transactions and upserts, Docker and Docker Compose, container networking, Apache Airflow (DAGs, retries, callbacks, catchup), pytest and coverage, decision records, reading logs and debugging on Windows.

## Goals for Week 4

- Finish the README and the final reflection.
- Tag the repo `v1.0`.
- Prepare and deliver the showcase, with a backup recording.

## Questions I still have

- How would I run Airflow on a server so a laptop restart does not stop the schedule?
- How should I set up CI so the PostgreSQL tests run on every push?
