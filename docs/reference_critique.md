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

> **Evidence level:** this table is built from the repo's `README.md`. Before you submit, check these against `IMPLEMENTATION.md` and the `weather_flow/` code: the Kafka topic name, whether the Spark job really streams, the Airflow schedule, which dashboard framework is actually run, and what is really stored in PostgreSQL.

## Architecture diagram

<!-- TODO: add Mermaid diagram labelled E / T / L -->

## Critique

<!-- TODO: 300-400 words: strengths, at least 3 problems with evidence, essential vs overkill -->