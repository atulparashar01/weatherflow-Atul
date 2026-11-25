# ADR 002: Airflow and the warehouse share a Docker network

Status: Accepted

## Context

WeatherFlow now runs as two separate Docker Compose projects:

- the project root: the `warehouse` (PostgreSQL 18) and the `pipeline` image;
- `orchestration/`: Apache Airflow 3.4.0 (apiserver, scheduler, DAG processor,
  triggerer, Celery worker, plus Airflow's own PostgreSQL and Redis).

Each Compose project gets its own private network, so by default an Airflow task
cannot reach the `warehouse` container. The DAG tasks run
`python -m weatherflow run ...`, which needs to connect to the warehouse.

Airflow also has its own PostgreSQL database, for its metadata (DAG runs, task
states, logs). The warehouse data must not be stored there.

## Decision

Create one named Docker network, `weatherflow-net`.

- The root `docker-compose.yml` creates it (`name: weatherflow-net`) and puts the
  `warehouse` service on it, next to its default network.
- `orchestration/docker-compose.yaml` declares it as `external: true` and puts
  all Airflow services on it, next to their default network.
- Airflow tasks connect to `warehouse:5432` through `DATABASE_URL`, which is set
  in the git-ignored `orchestration/.env`.
- The two Compose projects stay separate: they can be started, stopped and
  rebuilt independently. The warehouse must be started first, because the
  network is created by the root project.

## Consequences

- The warehouse data stays in the `warehouse` container and its `pgdata` volume.
  Airflow's own database holds only orchestration metadata.
- Only the containers that need it are on the shared network. Airflow's Redis
  and PostgreSQL stay on Airflow's default network and are not visible to the
  warehouse.
- The warehouse is not exposed to the internet. The host port 5433 is unchanged,
  and Airflow does not use it.
- If the warehouse is not running, Airflow tasks fail with a connection error
  and are retried by the DAG's retry settings.
- The root project must be started before Airflow, or `docker compose up` in
  `orchestration/` stops with "network weatherflow-net declared as external, but
  could not be found".

## Alternatives considered

- **One big Compose file for everything.** Simple networking, but it ties the
  warehouse and Airflow lifecycles together and makes the warehouse stack
  heavier to run on its own.
- **Airflow connects through the host (`host.docker.internal:5433`).** Works on
  Docker Desktop but depends on the host, is not portable to Linux hosts, and
  sends traffic out of Docker and back in.
- **Store the data in Airflow's own PostgreSQL.** Rejected: it mixes business
  data with orchestration metadata, so resetting, upgrading or backing up
  Airflow would put the data at risk.
