# Grafana Dashboard for API Telemetry

A small weather API (using [Open-Meteo](https://open-meteo.com/)) that exposes metrics, which **Prometheus** collects and **Grafana** shows as live graphs of **request rate, latency and error rate**. Everything runs with **Docker Compose**.

## Team and roles

| Member | GitHub | Role | Owns |
|---|---|---|---|
| Krish Kalsi | [@KrishKalsi](https://github.com/KrishKalsi) | Telemetry and alerting | Repo setup, Prometheus metrics instrumentation, alert rules, traffic generator, architecture |
| Jaival Katira | [@JaivalKatira](https://github.com/JaivalKatira) | Backend developer | Weather API, Open-Meteo integration, caching, unit tests |
|  |  | DevOps / infrastructure | Dockerfile, Docker Compose, Prometheus scraping |
|  |  | Observability / dashboards | Grafana setup and provisioning, telemetry dashboard |

## Architecture

```mermaid
flowchart LR
    U["User / browser<br/>scripts/traffic.py"] -->|"GET /weather?city=delhi"| API

    subgraph DC["Docker Compose network"]
        API["Weather API<br/>FastAPI :8000<br/>in-memory cache"]
        P["Prometheus :9090<br/>time-series database"]
        G["Grafana :3000<br/>dashboard"]
        P -->|"scrape GET /metrics every 5s"| API
        G -->|"PromQL queries"| P
    end

    API -->|"cache miss only<br/>max once per city per 10 min"| OM["Open-Meteo<br/>public weather API"]
    You["You"] -->|"open localhost:3000"| G
```

**How a request flows**

1. A user (or `scripts/traffic.py`) calls `GET /weather?city=delhi` on our API.
2. The API checks its cache. On a **miss**, it calls Open-Meteo and saves the result for 10 minutes. On a **hit**, it answers straight away.
3. A middleware in the API times every request and updates two metrics: `http_requests_total` (counter) and `http_request_duration_seconds` (histogram).
4. Every 5 seconds **Prometheus** scrapes `GET /metrics` and stores the numbers with a timestamp.
5. **Grafana** asks Prometheus for the numbers with PromQL and draws request rate, latency (p50/p95/p99) and error rate.

## Tech stack

- **Python 3.12 + FastAPI**: the weather API
- **Open-Meteo**: free weather data, no API key needed
- **prometheus-client**: exposes metrics on `/metrics`
- **Prometheus**: scrapes and stores the metrics
- **Grafana**: dashboards
- **Docker Compose**: runs everything with one command
- **GitHub Actions**: CI that runs tests and checks configs on every push and PR

## Setup and run

_Coming soon._

## Screenshots

_Coming soon._

## Research questions

### 1. What are metrics, logs and traces?

**Metrics** are numbers measured over time, for example "requests per second" or "how long a request took". They are small and cheap to store, so they are good for graphs and alerts. Our API exposes metrics on `/metrics`: a counter `http_requests_total` (how many requests, split by path and status code) and a histogram `http_request_duration_seconds` (how long they took).

**Logs** are text lines that describe single events, for example `GET /weather -> 404 in 0.003s`. They have more detail than metrics, so they help you find out *why* something happened, but they take more space. Our API prints one log line per request (see `docker compose logs api`).

**Traces** follow one request across every service it passes through, and show how long each step took. If our API called a database and two other services, a trace would show which of those steps was slow. We don't use traces because our system has only one service, but tools like OpenTelemetry and Jaeger do this.

**In short:** metrics tell you *that* something is wrong (error rate went up), logs tell you *what* happened (which requests failed), and traces tell you *where* it happened (which service or step was slow).

### 2. How does Prometheus scrape data?

_TODO (DevOps): answer in your own words._

### 3. What do latency percentiles and error rate show?

_TODO (Observability): answer in your own words._

## Credits

- Weather data: [Open-Meteo](https://open-meteo.com/) (free, no key)
- Docs: [Prometheus](https://prometheus.io/docs/), [Grafana](https://grafana.com/docs/)
