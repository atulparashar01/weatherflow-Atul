# Week 1 Deliverables Checklist

| Done | Deliverable | Notes |
|:-:|---|---|
| [ ] | **D1.6** `docs/reflections/week_1.md` (use the template) | Draft written. Copy it into the template and add your own details |
| [ ] | **Skills tracker** updated | Add: Python venv, Git/GitHub, REST APIs, pandas, data profiling, SQL/SQLite, idempotent loads |
| [ ] | **Live Session 1** attended (Thu 5 Nov) | |
| [ ] | **Weekly update** posted (Tue 10 Nov, by 21:00) | |
| [ ] | **Show-and-tell** (3-5 min) ready for Live Session 2 (Thu 12 Nov, 20:00) | Demo plan below |

## Show-and-tell plan (3-5 min)

1. **The problem (20 s):** an events company needs trustworthy hourly weather for 5 UK cities.
2. **Live demo (about 2 min):** run `python etl_v1.py` and show `Loaded 240 rows`. Run it again to show it's still 240. Then run one SQL query from `sql/week1_queries.sql`.
3. **Reference critique (1 min):** a real API key printed in the README, docs that contradict themselves, and Kafka and Spark being overkill for about 120 readings a day.
4. **One lesson (30 s):** an unsaved notebook reached GitHub as an empty file, and `.gitignore` doesn't remove files that are already tracked.
5. **Next week (15 s):** star schema, data quality checks and pytest.

## Before the session

- [ ] Run `python etl_v1.py` once on the real API
- [ ] Open `weather.db` and the SQL file in the SQLite Viewer
- [ ] Keep `data/raw/` files ready in case the live API fails
- [ ] Video on, microphone tested