import random
import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_auth_trips_and_route_flow(client):
    unique_id = int(time.time())
    rand_num = random.randint(1000, 9999)
    username = f"testuser_{unique_id}_{rand_num}"
    vehicle_num = f"MH12AB{rand_num}"

    reg_payload = {
        "username": username,
        "password": "Password123!",
        "email": f"{username}@example.com",
        "vehicle_number": vehicle_num
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code in [200, 201]
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == username

    trips_res = client.get("/api/v1/trips", headers=headers)
    assert trips_res.status_code == 200
    trips_data = trips_res.json()
    assert isinstance(trips_data, list)

    route_payload = {
        "start_coords": [19.0760, 72.8777],
        "end_coords": [18.5204, 73.8567],
        "priority": "eco"
    }
    route_res = client.post("/api/v1/route/optimize", json=route_payload, headers=headers)
    assert route_res.status_code == 200
    route_data = route_res.json()
    assert route_data["success"] is True
    assert "routes" in route_data
    assert len(route_data["routes"]) > 0


def test_model_info(client):
    res = client.get("/api/v1/insights/model-info")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
