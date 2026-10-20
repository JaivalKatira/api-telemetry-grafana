**Metrics** are numbers measured over time, for example "requests per second" or "how long a request took". They are small and cheap to store, so they are good for graphs and alerts. Our API exposes metrics on `/metrics`: a counter `http_requests_total` (how many requests, split by path and status code) and a histogram `http_request_duration_seconds` (how long they took).

**Logs** are text lines that describe single events, for example `GET /weather -> 404 in 0.003s`. They have more detail than metrics, so they help you find out *why* something happened, but they take more space. Our API prints one log line per request (see `docker compose logs api`).

**Traces** follow one request across every service it passes through, and show how long each step took. If our API called a database and two other services, a trace would show which of those steps was slow. We don't use traces because our system has only one service, but tools like OpenTelemetry and Jaeger do this.

**In short:** metrics tell you *that* something is wrong (error rate went up), logs tell you *what* happened (which requests failed), and traces tell you *where* it happened (which service or step was slow).
