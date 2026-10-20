"""
Tests for the weather API. They never call the real Open-Meteo:
we replace fetch_weather with a fake so tests are fast and don't use up the API's limits.

Run from the app/ folder:  python -m pytest -v
"""

import httpx
import pytest
from fastapi.testclient import TestClient

import main

FAKE_RESPONSE = {
    "current": {
        "time": "2026-10-20T12:00",
        "temperature_2m": 31.2,
        "relative_humidity_2m": 48,
        "wind_speed_10m": 9.4,
        "weather_code": 1,
    }
}


@pytest.fixture
def client(monkeypatch):
    main._cache.clear()
    calls = {"count": 0}

    async def fake_fetch(lat, lon):
        calls["count"] += 1
        return FAKE_RESPONSE

    monkeypatch.setattr(main, "fetch_weather", fake_fetch)
    c = TestClient(main.app)
    c.calls = calls
    return c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_weather_known_city(client):
    resp = client.get("/weather", params={"city": "Delhi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "delhi"
    assert body["temperature_c"] == 31.2
    assert body["source"] == "open-meteo"


def test_unknown_city_returns_404(client):
    resp = client.get("/weather", params={"city": "atlantis"})
    assert resp.status_code == 404


def test_second_request_comes_from_cache(client):
    client.get("/weather", params={"city": "mumbai"})
    second = client.get("/weather", params={"city": "mumbai"})
    assert second.json()["source"] == "cache"
    assert client.calls["count"] == 1  # Open-Meteo was only called once


def test_upstream_failure_returns_502(client, monkeypatch):
    async def broken_fetch(lat, lon):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(main, "fetch_weather", broken_fetch)
    resp = client.get("/weather", params={"city": "pune"})
    assert resp.status_code == 502
