from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "ts" in body

def test_version():
    r = client.get("/api/version")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "n2o-container-guard"
    assert "version" in body
