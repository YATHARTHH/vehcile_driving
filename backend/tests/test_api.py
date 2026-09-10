from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data

def test_auth_trips_and_route_flow():
    # 1. Register new user with valid vehicle number format (e.g. MH12AB1234)
    import time
    username = f"testuser_{int(time.time())}"
    reg_payload = {
        "username": username,
        "password": "Password123!",
        "email": f"{username}@example.com",
        "vehicle_number": "MH12AB1234"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code in [200, 201]
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get me profile
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == username

    # 3. Get trips
    trips_res = client.get("/api/v1/trips", headers=headers)
    assert trips_res.status_code == 200
    trips_data = trips_res.json()
    assert isinstance(trips_data, list)

    # 4. Route Optimization API with auth header
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

def test_model_info():
    res = client.get("/api/v1/insights/model-info")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
