import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from main import app, get_db

# Override database dependency for unit tests so tests run offline without DB
async def override_get_db():
    yield None

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health_check_endpoint():
    """Verify cloud-native /health probe returns 200 and expected status keys."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data

def test_predict_eta_valid_payload():
    """Verify ML ETA prediction returns a valid numerical estimate."""
    payload = {
        "distance_km": 85.5,
        "num_stops": 2,
        "weather": "Clear",
        "time_of_day": "Morning",
        "traffic_level": "Moderate"
    }
    response = client.post("/predict_eta", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_eta_min" in data
    assert isinstance(data["predicted_eta_min"], (int, float))
    assert data["predicted_eta_min"] > 0

def test_predict_eta_missing_required_fields():
    """Verify Pydantic schema validation returns 422 on incomplete payloads."""
    payload = {
        "distance_km": 42.0
    }
    response = client.post("/predict_eta", json=payload)
    assert response.status_code == 422

def test_predict_eta_invalid_types():
    """Verify Pydantic schema validation rejects invalid data types."""
    payload = {
        "distance_km": "not-a-number",
        "num_stops": "invalid",
        "weather": "Rainy",
        "time_of_day": "Evening",
        "traffic_level": "Heavy"
    }
    response = client.post("/predict_eta", json=payload)
    assert response.status_code == 422

def test_unauthenticated_protected_route():
    """Verify RBAC / OAuth2 bearer protection on sensitive routes."""
    response = client.get("/history")
    assert response.status_code == 401

def test_suggest_locations_missing_query():
    """Verify query validation on location suggestion endpoint."""
    response = client.get("/suggest?query=")
    assert response.status_code == 400

def test_request_process_time_header():
    """Verify custom latency middleware adds X-Process-Time header."""
    response = client.get("/health")
    assert "X-Process-Time" in response.headers
