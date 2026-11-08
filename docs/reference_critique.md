# Reference Project Critique: WeatherFlow-DataEngineering

Reference repo: <https://github.com/SyedRoshanAli/WeatherFlow-DataEngineering>

## Component table

| Component | Tool used | What it does in this project | Batch or streaming? |
|---|---|---|---|
| **Data source** | WeatherAPI (primary), OpenWeatherMap (secondary, optional key), simulated weather station data | Provides current weather readings through REST API calls made by Python scripts in `scripts/`. WeatherAPI is the main source; OpenWeatherMap adds a second feed in a different format. | **Batch.** Each REST call is a request/response pull. Data only looks "streaming" once the producer publishes it to Kafka. |
| **Message broker** | Apache Kafka (with Kafdrop UI) | A producer container publishes each reading as a message to a topic, and a consumer container reads it. It decouples fetching data from processing it, and Kafdrop lets you inspect topics in the browser. | **Streaming.** Messages flow event by event. |
| **Processing** | Apache Spark (master container) | Transforms and analyses the weather data from Kafka: cleaning, reshaping and calculating summaries. Jobs live in `spark/`. | **Claimed real-time.** The README says data is processed "in real-time". Check the Spark job code to see whether it truly streams or just runs batch jobs. |
| **Orchestration** | Apache Airflow | Schedules and monitors the workflow through DAGs in `airflow/`. It runs the weather scripts, which are mounted into the Airflow container. It uses PostgreSQL to store its own run history. | **Batch.** Airflow runs tasks on a schedule. |
| **Storage** | Data lake with raw and processed zones (files under `data/`), plus PostgreSQL | Raw API data and processed output are kept as files in separate zones, with reports alongside. PostgreSQL is described as the database for Airflow metadata, not weather results. | **Batch.** Files are written in chunks, not row by row. |
| **Serving** | Flask web dashboard with ApexCharts.js | Shows weather insights as interactive charts. Users can add a new city through the UI, and the dashboard fetches and displays its data. The README also mentions a Streamlit script, so the real dashboard framework needs checking. | **Neither.** It is request-driven: data updates when the page loads or a user adds a city. |
| **Packaging** | Docker Compose | Starts the whole platform with `docker-compose up -d`: Airflow, PostgreSQL, Kafka, Kafdrop, Spark, the producer, the consumer and the dashboard. All containers share one network (`weather-network`) and expose fixed ports. | **Neither.** It is infrastructure. |

## Critique

**What it does well.** Each concern has its own folder and container (ingestion, processing, orchestration, storage, serving), so one part can change without breaking the rest. The Kafka topic also decouples fetching from processing. Raw and processed zones in the data lake allow reprocessing, and Docker Compose starts the whole platform with one command.

**Problems and risks.**

1. **Secrets exposed.** The README prints a real WeatherAPI key beside "already configured", then repeats it in the `.env` example, a Python test one-liner and the Data Sources list. The Airflow login is also published ("username: admin, password: admin"). It should use a placeholder like `your_weatherapi_key`, keep the real key in an ignored `.env`, commit a `.env.example`, and revoke the leaked key.
2. **Documentation contradicts itself.** The repo description says data is stored in PostgreSQL, but the README calls PostgreSQL the "Database for Airflow metadata" and describes a data lake for storage. The dashboard is Flask on port 8051, yet the README also says to run `streamlit_dashboard.py` on port 8501, a file missing from the Project Structure tree. That tree lists `README.md` and `requirements.txt` inside `weather_flow/`, and `test_weather_api.py` sits at the repo root, outside `tests/`.
3. **Weak testing and monitoring.** "Verifying Components" relies on manual `docker logs` commands and a hand-made `weather_test` table filled with Berlin and Tokyo. Nothing would alert anyone if the producer stopped, and there are no automated tests or CI. Better: Airflow retries and failure alerts, freshness and row-count checks, and pytest running in GitHub Actions.

**Essential vs overkill.** Five cities every hour is about 120 readings a day. Essential: a scheduler (Airflow, or even cron), a Python extract step, a database such as PostgreSQL, a dashboard, and Docker for repeatable setup. Overkill: Kafka and Spark. Kafka suits continuous, high-volume events, but this source updates once an hour, so the broker only adds failure points. Spark spreads work across machines, yet 120 rows fit comfortably in pandas. The README's "real-time" goal is unnecessary when the data itself is hourly.