# Final Reflection: WeatherFlow

**Name:** Atul Parashar
**Programme:** London Success Academy, Data Engineering internship (Weeks 1 to 3, showcase in Week 4)
**Repo:** https://github.com/atulparashar01/weatherflow-Atul

## The problem and what I built

An events company needs to know where outdoor work is risky, hour by hour, in five UK cities. WeatherFlow collects hourly weather for London, Manchester, Birmingham, Edinburgh and Cardiff from two independent sources (Open-Meteo and WeatherAPI.com), checks the data, works out an outdoor work risk (low, medium or high), and stores everything in a PostgreSQL warehouse. It runs in Docker, and Airflow starts it every hour.

## How it fits together

1. **Extract:** call each API with retries and timeouts, and save the raw response unchanged.
2. **Transform:** flatten to one row per city per hour per source, convert units, add weather descriptions, the Beaufort scale and `outdoor_work_risk`, and store times in UTC.
3. **Validate:** data quality checks. Bad rows are quarantined with a reason, serious problems stop the run, and soft problems only warn. A cross-source check warns when the two sources differ by more than 3 °C.
4. **Load:** an upsert into a star schema (`dim_city`, `dim_date`, `fact_weather_hourly`) in one transaction, so a failed load saves nothing and a repeated load changes nothing.
5. **Run:** `python -m weatherflow run`, as a container, or hourly from Airflow with 2 retries and an alert when a task finally fails.

## What I learned across the three weeks

- **Make everything safe to repeat.** A primary key, an upsert and one transaction mean a run can be repeated or retried without duplicating or losing rows. This one idea is why Airflow retries and backfills are safe.
- **Data quality is a design decision.** Deciding what to quarantine, what to warn about and what to stop for matters more than the checks themselves.
- **Never trust a field you did not verify.** WeatherAPI's `time` field does not say which timezone it uses. I proved that `time_epoch` is the real instant before trusting it (ADR 003).
- **Secrets are a habit.** The key lives only in `.env`, never in a log line, an image or Git, and I searched for it to prove that.
- **Containers and orchestration have clear jobs.** Docker makes the run identical everywhere, Airflow decides when it happens and what to do when it fails, and the warehouse is a separate service that keeps the data (ADR 002).
- **Prove the failure path.** A pipeline you have only seen succeed is not tested. I forced a missing key, a mid-load error, a wrong key in Airflow, and a repeated run.
- **Write down decisions when you make them.** ADRs 001, 002 and 003 explain why the second source, the shared network and the time handling are the way they are.

## What was hard

- **Windows tooling.** A `.env` that became a folder, the Microsoft Store `python` alias, Git Bash rewriting Docker paths, and OneDrive prompts. They looked like code bugs until I read the error.
- **Docker image problems.** File ownership and a copied `egg-info` folder broke the Airflow image build until I fixed them.
- **Doing things in the wrong place.** A command run in the wrong folder once appended a wrong line to my real `.env`. I now check `pwd` and `git status` first.
- **Keeping tests honest.** My first coverage figure left out three modules. The real total was lower, and I corrected it.
- **Time.** I did not have time for CI (Task 3.5) or the dashboard and alert channel (Task 3.6). I wrote ADR 003 but not the rest.

## What went well

- The full chain works end to end and was proved from a fresh clone: it built from nothing, ran with exit code 0, and loaded 240 and 120 rows into an empty warehouse.
- 49 automated tests pass with 74% coverage, and none of them calls the real API.
- Airflow ran the pipeline every hour. A deliberate failure was retried twice and then alerted, and re-running a past hour left the counts unchanged.

## What I would do next

- **CI:** run the tests and a PostgreSQL integration test on every push, with a 70% coverage gate, so a broken change cannot reach `main`.
- **Dashboard:** a page that answers "where is outdoor work risky in the next 24 hours?", with times in UK time and a clear warning when the data is old.
- **Alerts:** send the high-risk and failure alerts to a real channel, with no duplicates, using an `alerts_sent` table.
- **Tests for `pipeline.py`,** the weakest module at 35% coverage.
- **Run Airflow on a server,** so a laptop restart cannot skip hours.

## What I would tell the client

The pipeline collects hourly weather for five UK cities from two independent sources, checks it, and flags the hours where outdoor work is high risk. It repeats safely, it tells you when it fails, and every choice is written down. The next step is a screen that shows tomorrow's risk at a glance and a message that reaches your team before a storm does.

## Skills practised

Python packaging and a command-line interface, REST APIs and secrets handling, pandas, Parquet, star schema design, PostgreSQL and psycopg 3, transactions and upserts, data quality checks and quarantine, pytest and coverage, Docker and Docker Compose, container networking, Apache Airflow (DAGs, retries, callbacks), Git and GitHub with branches and pull requests, architecture decision records, debugging on Windows.
