FROM apache/airflow:3.4.0

ENV WEATHERFLOW_CONFIG=/opt/weatherflow/config.yaml

# Folders the pipeline writes to must belong to the airflow user
USER root
RUN mkdir -p /opt/weatherflow/data /opt/weatherflow/docs/dq_reports \
    && chown -R airflow:root /opt/weatherflow
USER airflow

# 1. Dependencies first (this layer is cached). apache-airflow is pinned,
#    so pip can never change Airflow itself.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir "apache-airflow==3.4.0" -r /tmp/requirements.txt

# 2. Our package (owned by airflow so pip can write its build files)
COPY --chown=airflow:root pyproject.toml /tmp/weatherflow/pyproject.toml
COPY --chown=airflow:root src /tmp/weatherflow/src
RUN pip install --no-cache-dir "apache-airflow==3.4.0" /tmp/weatherflow

# 3. Files the pipeline reads at run time
COPY --chown=airflow:root config.yaml /opt/weatherflow/config.yaml
COPY --chown=airflow:root sql /opt/weatherflow/sql