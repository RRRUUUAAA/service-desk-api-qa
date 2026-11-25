from typing import Any

import requests


def assert_error(
    response: requests.Response,
    expected_status: int,
    detail_contains: str | None = None,
) -> dict[str, Any]:
    assert response.status_code == expected_status, (
        f"Expected HTTP {expected_status}, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    assert "detail" in body
    if detail_contains is not None:
        assert detail_contains.lower() in str(body["detail"]).lower()
    return body


def assert_pagination(
    body: dict[str, Any],
    *,
    page: int,
    page_size: int,
) -> None:
    assert body["page"] == page
    assert body["page_size"] == page_size
    assert body["total"] >= len(body["items"])
    assert len(body["items"]) <= page_size


def assert_ticket_db_row(
    row: dict[str, Any],
    *,
    ticket_id: int,
    created_by: int,
    status: str,
    priority: str,
    assignee_id: int | None = None,
) -> None:
    assert row["id"] == ticket_id
    assert row["created_by"] == created_by
    assert row["status"] == status
    assert row["priority"] == priority
    assert row["assignee_id"] == assignee_id
