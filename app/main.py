"""
Weather API with Prometheus metrics.

What this service does:
  1. GET /weather?city=delhi  -> asks Open-Meteo for the current weather and returns it
  2. GET /metrics             -> plain-text numbers that Prometheus reads ("scrapes")

Every request is measured by the middleware below:
  - how many requests came in        (Counter   -> request rate, error rate)
  - how long each request took       (Histogram -> latency p50 / p95 / p99)
"""

import logging
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ---------------------------------------------------------------------------
# Settings (can be changed with environment variables, see .env.example)
# ---------------------------------------------------------------------------
OPEN_METEO_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))  # 10 minutes
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))

# Cities we support, with their coordinates (Open-Meteo needs latitude/longitude).
CITIES = {
    "delhi": (28.61, 77.21),
    "mumbai": (19.08, 72.88),
    "bengaluru": (12.97, 77.59),
    "chennai": (13.08, 80.27),
    "kolkata": (22.57, 88.36),
    "hyderabad": (17.39, 78.49),
    "pune": (18.52, 73.86),
    "jaipur": (26.91, 75.79),
    "london": (51.51, -0.13),
    "new-york": (40.71, -74.01),
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("weather-api")

app = FastAPI(title="Weather API", version="1.0.0")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
# Counter: a number that only goes up. Prometheus turns it into "per second" with rate().
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status"],
)

# Histogram: sorts each request's duration into "buckets" so we can compute percentiles.
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Time spent handling an HTTP request",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# How long the call to Open-Meteo itself takes (so we can see if the slowness is "them" or "us").
UPSTREAM_LATENCY = Histogram(
    "upstream_request_duration_seconds",
    "Time spent waiting for Open-Meteo",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

CACHE_EVENTS = Counter(
    "weather_cache_events_total",
    "Cache hits and misses for weather lookups",
    ["result"],  # "hit" or "miss"
)


@app.middleware("http")
async def measure_requests(request: Request, call_next):
    """Runs around every request: start a timer, handle the request, record the numbers."""
    start = time.perf_counter()
    status = 500  # if the handler crashes, we still count it as a 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        # Use the route template ("/weather"), not the raw URL, so labels stay few and tidy.
        route = request.scope.get("route")
        path = route.path if route else "unknown"
        if path != "/metrics":  # don't measure Prometheus reading the metrics
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(duration)
            log.info("%s %s -> %s in %.3fs", request.method, request.url.path, status, duration)


# ---------------------------------------------------------------------------
# Simple in-memory cache: {city: (time_saved, data)}
# Respects Open-Meteo's rate limits: each city is fetched at most once per CACHE_TTL_SECONDS.
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, dict]] = {}


async def fetch_weather(lat: float, lon: float) -> dict:
    """Call Open-Meteo and return its JSON."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    }
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            return resp.json()
    finally:
        UPSTREAM_LATENCY.observe(time.perf_counter() - start)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "weather-api", "try": "/weather?city=delhi", "cities": "/cities"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cities")
def cities():
    return {"cities": sorted(CITIES)}


@app.get("/weather")
async def weather(city: str = Query(..., description="City name, e.g. delhi")):
    key = city.strip().lower()
    if key not in CITIES:
        # 404 = the client asked for something we don't have (shows up as a 4xx error)
        raise HTTPException(status_code=404, detail=f"Unknown city '{city}'. See /cities")

    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        CACHE_EVENTS.labels("hit").inc()
        data, source = cached[1], "cache"
    else:
        CACHE_EVENTS.labels("miss").inc()
        lat, lon = CITIES[key]
        try:
            data = await fetch_weather(lat, lon)
        except httpx.HTTPError as exc:
            # 502 = the service we depend on failed (shows up as a 5xx error)
            log.warning("Open-Meteo request failed: %s", exc)
            raise HTTPException(status_code=502, detail="Weather provider unavailable")
        _cache[key] = (time.time(), data)
        source = "open-meteo"

    current = data.get("current", {})
    return {
        "city": key,
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "observed_at": current.get("time"),
        "source": source,
    }


@app.get("/metrics")
def metrics():
    """Prometheus reads this page every few seconds."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
