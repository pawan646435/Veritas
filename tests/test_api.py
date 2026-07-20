from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_routes_are_registered():
    """A lightweight structural check — confirms the routes exist without
    actually calling them, since /audits/run and /audits/report need a
    real Groq key and a real database to do anything meaningful.

    Checks the OpenAPI schema (FastAPI's own public interface for this)
    rather than app.routes directly — internal route object structure can
    change between framework versions; the OpenAPI schema is the stable,
    public contract.
    """
    openapi_schema = app.openapi()
    assert "/audits/run" in openapi_schema["paths"]
    assert "/audits/report" in openapi_schema["paths"]
