# Grafana Dashboard for API Telemetry

A small weather API (using [Open-Meteo](https://open-meteo.com/)) that exposes metrics, which **Prometheus** collects and **Grafana** shows as live graphs of **request rate, latency and error rate**. Everything runs with **Docker Compose**.

## Team and roles

| Member | GitHub | Role | Owns |
|---|---|---|---|
| Krish Kalsi | [@KrishKalsi](https://github.com/KrishKalsi) | Telemetry and CI | Repo setup, Prometheus metrics instrumentation, alert rules, traffic generator, architecture |
| Jaival Katira | [@JaivalKatira](https://github.com/JaivalKatira) | Backend developer | Weather API, Open-Meteo integration, caching, unit tests |
|  |  | DevOps / infrastructure | Dockerfile, Docker Compose, Prometheus scraping |
|  |  | Observability / dashboards | Grafana setup and provisioning, telemetry dashboard |

## Architecture

_Coming soon._

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

_TODO (Backend developer): answer in your own words._

### 2. How does Prometheus scrape data?

_TODO (DevOps): answer in your own words._

### 3. What do latency percentiles and error rate show?

_TODO (Observability): answer in your own words._

## Credits

- Weather data: [Open-Meteo](https://open-meteo.com/) (free, no key)
- Docs: [Prometheus](https://prometheus.io/docs/), [Grafana](https://grafana.com/docs/)
