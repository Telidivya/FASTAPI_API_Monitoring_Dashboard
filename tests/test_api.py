from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_users_and_products():
    assert client.get("/users").status_code == 200
    assert client.get("/products").status_code == 200


def test_protected_requires_auth():
    response = client.get("/protected")
    assert response.status_code == 401
    response = client.get("/protected", headers={"Authorization": "Bearer demo-secret-token"})
    assert response.status_code == 200


def test_simulated_server_error():
    assert client.get("/simulate-error").status_code == 500


def test_simulated_rate_limit():
    # Use a unique client IP in TestClient to avoid shared rate-limit state.
    limited_client = TestClient(app, client=("192.0.2.20", 12345))
    statuses = [limited_client.get("/simulate-rate-limit").status_code for _ in range(7)]
    assert 429 in statuses


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "api_requests_total" in response.text
