import pytest

from tests.framework.api_client import ApiClient


pytestmark = pytest.mark.integration


def test_health_endpoint_returns_ok(anonymous_api: ApiClient) -> None:
    response = anonymous_api.health()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_openapi_document_exposes_core_resources(anonymous_api: ApiClient) -> None:
    response = anonymous_api.request("GET", "/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/auth/login" in paths
    assert "/users" in paths
    assert "/tickets" in paths
    assert "/tickets/{ticket_id}/assign" in paths
