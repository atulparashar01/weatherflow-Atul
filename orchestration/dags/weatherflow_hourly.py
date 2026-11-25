"""WeatherFlow hourly DAG.

Runs the pipeline for each source, then checks for risk alerts.

Secrets (WEATHERAPI_KEY, DATABASE_URL) are not in this file. They come from the
container environment, which Airflow gets from orchestration/.env.
"""

import logging
from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

log = logging.getLogger(__name__)

# The image keeps the pipeline's config, sql and data folders here.
WORKDIR = "/opt/weatherflow"


def alert_on_failure(context):
    """Called when a task has failed (after its retries are used up)."""
    ti = context["task_instance"]
    log.error(
        "ALERT: task %s of DAG %s failed (run %s, try %s)",
        ti.task_id,
        ti.dag_id,
        context["dag_run"].run_id,
        ti.try_number,
    )


default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": alert_on_failure,
}


@dag(
    dag_id="weatherflow_hourly",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 11, 24, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["weatherflow"],
)
def weatherflow_hourly():
    run_open_meteo = BashOperator(
        task_id="run_open_meteo",
        bash_command="python -m weatherflow run --source open_meteo",
        cwd=WORKDIR,
    )
    run_weatherapi = BashOperator(
        task_id="run_weatherapi",
        bash_command="python -m weatherflow run --source weatherapi",
        cwd=WORKDIR,
    )
    # Placeholder: the `alerts` command does not exist yet (the alert channel is Task 3.6).
    # When it exists, change the command to: python -m weatherflow alerts
    check_risk_alerts = BashOperator(
        task_id="check_risk_alerts",
        bash_command='echo "check_risk_alerts: placeholder, the alerts command comes with Task 3.6"',
        cwd=WORKDIR,
    )

    run_open_meteo >> run_weatherapi >> check_risk_alerts


weatherflow_hourly()