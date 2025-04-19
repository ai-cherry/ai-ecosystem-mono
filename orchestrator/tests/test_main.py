import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_process_endpoint():
    payload = {"test": "value"}
    response = client.post("/api/v1/process/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Process endpoint called"
    assert data["input"] == payload