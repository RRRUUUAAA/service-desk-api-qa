import pytest

from tests.framework.api_client import ApiClient
from tests.framework.assertions import assert_error, assert_ticket_db_row
from tests.framework.db_client import DatabaseClient
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def _track_created_ticket(
    data_factory: DataFactory,
    response,
) -> dict:
    assert response.status_code == 201, response.text
    ticket = response.json()
    data_factory.created_ticket_ids.append(ticket["id"])
    return ticket


def test_employee_can_create_ticket_and_audit_event_is_persisted(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    title = f"Laptop will not boot {data_factory.run_id}"

    response = employee.api.create_ticket(
        {
            "title": title,
            "description": "Power light is on but the screen remains black.",
            "priority": "high",
        }
    )
    ticket = _track_created_ticket(data_factory, response)

    assert ticket["title"] == title
    assert ticket["status"] == "open"
    assert ticket["created_by"] == employee.id
    assert ticket["assignee_id"] is None
    assert len(ticket["events"]) == 1
    assert ticket["events"][0]["event_type"] == "created"
    assert ticket["events"][0]["from_status"] is None
    assert ticket["events"][0]["to_status"] == "open"

    row = db_client.fetch_one(
        """
        SELECT id, created_by, assignee_id, status, priority, title, description
        FROM tickets
        WHERE id = :ticket_id
        """,
        {"ticket_id": ticket["id"]},
    )
    assert row is not None
    assert_ticket_db_row(
        row,
        ticket_id=ticket["id"],
        created_by=employee.id,
        status="open",
        priority="high",
    )
    assert row["title"] == title

    event = db_client.fetch_one(
        """
        SELECT actor_id, event_type, from_status, to_status
        FROM ticket_events
        WHERE ticket_id = :ticket_id
        ORDER BY id ASC
        LIMIT 1
        """,
        {"ticket_id": ticket["id"]},
    )
    assert event == {
        "actor_id": employee.id,
        "event_type": "created",
        "from_status": None,
        "to_status": "open",
    }


@pytest.mark.parametrize(
    ("title_length", "expected_status"),
    [(1, 201), (120, 201), (121, 422)],
)
def test_ticket_title_length_boundary(
    employee: Actor,
    data_factory: DataFactory,
    title_length: int,
    expected_status: int,
) -> None:
    response = employee.api.create_ticket({"title": "x" * title_length})

    assert response.status_code == expected_status
    if expected_status == 201:
        ticket = response.json()
        data_factory.created_ticket_ids.append(ticket["id"])
        assert len(ticket["title"]) == title_length


def test_ticket_title_cannot_be_whitespace_only(employee: Actor) -> None:
    response = employee.api.create_ticket({"title": "   "})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ticket_creation_requires_title(employee: Actor) -> None:
    response = employee.api.create_ticket({"description": "missing title"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("description_length", "expected_status"),
    [(2000, 201), (2001, 422)],
)
def test_ticket_description_length_boundary(
    employee: Actor,
    data_factory: DataFactory,
    description_length: int,
    expected_status: int,
) -> None:
    response = employee.api.create_ticket(
        {
            "title": f"Description boundary {data_factory.run_id}",
            "description": "d" * description_length,
        }
    )

    assert response.status_code == expected_status
    if expected_status == 201:
        data_factory.created_ticket_ids.append(response.json()["id"])


def test_ticket_rejects_unknown_priority(employee: Actor) -> None:
    response = employee.api.create_ticket(
        {"title": "Invalid priority", "priority": "urgent"}
    )

    assert response.status_code == 422


def test_anonymous_user_cannot_create_ticket(anonymous_api: ApiClient) -> None:
    response = anonymous_api.create_ticket({"title": "Anonymous ticket"})

    assert_error(response, 401, "authentication required")


def test_employee_can_read_own_ticket(employee: Actor, data_factory: DataFactory) -> None:
    created = data_factory.create_ticket(employee, title="Own ticket")

    response = employee.api.get_ticket(created["id"])

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["created_by"] == employee.id


def test_employee_cannot_read_another_users_ticket(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    other = data_factory.create_user("employee")
    other_ticket = data_factory.create_ticket(other, title="Private ticket")

    response = employee.api.get_ticket(other_ticket["id"])

    assert_error(response, 404, "ticket not found")


def test_admin_can_read_any_ticket(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Admin visibility")

    response = admin_actor.api.get_ticket(ticket["id"])

    assert response.status_code == 200
    assert response.json()["id"] == ticket["id"]


def test_get_nonexistent_ticket_returns_404(employee: Actor) -> None:
    response = employee.api.get_ticket(2_000_000_000)

    assert_error(response, 404, "ticket not found")


def test_creator_can_update_open_ticket_and_database_matches(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Original title")
    updated_title = f"Updated title {data_factory.run_id}"

    response = employee.api.update_ticket(
        ticket["id"],
        {"title": updated_title, "priority": "high"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == updated_title
    assert response.json()["priority"] == "high"
    row = db_client.fetch_one(
        """
        SELECT title, priority, status
        FROM tickets
        WHERE id = :ticket_id
        """,
        {"ticket_id": ticket["id"]},
    )
    assert row is not None
    assert row["title"] == updated_title
    assert row["priority"] == "high"
    assert row["status"] == "open"


def test_non_owner_cannot_update_ticket(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    owner = data_factory.create_user("employee")
    ticket = data_factory.create_ticket(owner, title="Owner only")

    response = employee.api.update_ticket(ticket["id"], {"title": "Hijacked"})

    assert_error(response, 404, "ticket not found")
    row = db_client.fetch_one(
        "SELECT title FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row is not None
    assert row["title"] == "Owner only"


def test_update_requires_at_least_one_field(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(employee, title="No-op update")

    response = employee.api.update_ticket(ticket["id"], {})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"description": None},
        {"priority": None},
    ],
)
def test_update_rejects_explicit_null_fields(
    employee: Actor,
    data_factory: DataFactory,
    payload: dict,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Reject null update")

    response = employee.api.update_ticket(ticket["id"], payload)

    assert response.status_code == 422


def test_creator_cannot_edit_ticket_after_assignment(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Assigned ticket")
    data_factory.assign_ticket(ticket["id"], technician)

    response = employee.api.update_ticket(ticket["id"], {"title": "Edited too late"})

    assert_error(response, 409, "only open tickets")
    row = db_client.fetch_one(
        "SELECT title FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row is not None
    assert row["title"] == "Assigned ticket"


def test_employee_cannot_delete_ticket(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Cannot delete")

    response = employee.api.delete_ticket(ticket["id"])

    assert_error(response, 403, "insufficient permissions")
    count = db_client.scalar(
        "SELECT COUNT(*) FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert count == 1


def test_admin_delete_removes_ticket_and_events(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Delete me")

    response = admin_actor.api.delete_ticket(ticket["id"])

    assert response.status_code == 204
    assert response.content == b""
    ticket_count = db_client.scalar(
        "SELECT COUNT(*) FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    event_count = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert ticket_count == 0
    assert event_count == 0


def test_delete_nonexistent_ticket_returns_404(admin_actor: Actor) -> None:
    response = admin_actor.api.delete_ticket(2_000_000_000)

    assert_error(response, 404, "ticket not found")
