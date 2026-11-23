FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    WEATHERFLOW_CONFIG=/app/config.yaml

WORKDIR /app

# 1. Dependencies first. This layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Then our own code and the files it reads at run time.
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .
COPY config.yaml .
COPY sql ./sql

# 3. Run as a normal user, not root. It needs to write into data/ and docs/.
RUN useradd --create-home appuser \
    && mkdir -p /app/data /app/docs/dq_reports \
    && chown -R appuser /app
USER appuser

ENTRYPOINT ["python", "-m", "weatherflow"]
CMD ["run"]