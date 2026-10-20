"""
Weather API.

What this service does:
  GET /weather?city=delhi  -> asks Open-Meteo for the current weather and returns it
"""

import logging
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Query

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
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        return resp.json()


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
        # 404 = the client asked for something we don't have
        raise HTTPException(status_code=404, detail=f"Unknown city '{city}'. See /cities")

    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        data, source = cached[1], "cache"
    else:
        lat, lon = CITIES[key]
        try:
            data = await fetch_weather(lat, lon)
        except httpx.HTTPError as exc:
            # 502 = the service we depend on failed
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
