"""
Tests for Root and Health Check Endpoints.
"""

from fastapi.testclient import TestClient
from app.core.config import settings


def test_read_root(client: TestClient):
    """
    Test that the root endpoint (GET /) returns status 200 and valid JSON metadata.
    """
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert settings.PROJECT_NAME in data["message"]
    assert data["docs"] == "/docs"
    assert data["health"] == f"{settings.API_V1_STR}/health"


def test_health_check(client: TestClient):
    """
    Test that the health check endpoint (GET /api/v1/health) returns 200 and operational status.
    """
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.PROJECT_NAME
    assert data["version"] == settings.PROJECT_VERSION
    assert "timestamp" in data
    assert "debug" in data


def test_swagger_documentation(client: TestClient):
    """
    Test that Swagger UI (/docs) and OpenAPI JSON (/openapi.json) are accessible.
    """
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    openapi_json = openapi_response.json()
    assert openapi_json["info"]["title"] == settings.PROJECT_NAME
