import os
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from main import app, get_db

# Override database dependency for unit tests so tests run offline
async def override_get_db():
    yield None

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health_check():
    """Verify health endpoint returns status 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"

def test_predict_eta_endpoint():
    """Verify ETA prediction endpoint handles requests."""
    payload = {
        "distance_km": 100.0,
        "num_stops": 2,
        "weather": "Clear",
        "time_of_day": "Morning",
        "traffic_level": "Moderate"
    }
    response = client.post("/predict_eta", json=payload)
    assert response.status_code == 200

def test_predict_eta_missing_data():
    """Verify 422 error on missing required fields."""
    response = client.post("/predict_eta", json={"distance_km": 10.0})
    assert response.status_code == 422

def test_protected_route_without_token():
    """Verify unauthorized request returns 401."""
    response = client.get("/history")
    assert response.status_code == 401

def test_latency_header():
    """Verify latency middleware adds process time header."""
    response = client.get("/health")
    assert "X-Process-Time" in response.headers
