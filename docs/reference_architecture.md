````markdown
```mermaid
flowchart LR
  API[Weather APIs] --> P[Kafka producer]
  P --> T[(Kafka topic: weather-raw-data)]
  T --> S[Spark processor]
  S --> ...
```
````
