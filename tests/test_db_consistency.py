import uuid

import pytest

from tests.framework.assertions import assert_error
from tests.framework.db_client import DatabaseClient
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def test_assignment_foreign_key_resolves_to_technician(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="FK consistency")
    data_factory.assign_ticket(ticket["id"], technician)

    row = db_client.fetch_one(
        """
        SELECT t.id, t.assignee_id, u.role AS assignee_role, u.is_active
        FROM tickets AS t
        JOIN users AS u ON u.id = t.assignee_id
        WHERE t.id = :ticket_id
        """,
        {"ticket_id": ticket["id"]},
    )

    assert row is not None
    assert row["assignee_id"] == technician.id
    assert row["assignee_role"] == "technician"
    assert row["is_active"] is True


def test_duplicate_user_attempt_does_not_change_database(
    admin_actor: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    payload = {
        "username": f"dup_{suffix}",
        "email": f"dup_{suffix}@example.com",
        "password": "ValidPass123!",
        "role": "employee",
    }
    created = admin_actor.api.create_user(payload)
    assert created.status_code == 201
    data_factory.created_user_ids.append(created.json()["id"])

    response = admin_actor.api.create_user(
        {
            **payload,
            "email": f"unique_{suffix}@example.com",
        }
    )

    assert_error(response, 409)
    count = db_client.scalar(
        "SELECT COUNT(*) FROM users WHERE username = :username",
        {"username": payload["username"]},
    )
    assert count == 1


def test_api_list_total_matches_database_visibility_scope(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    data_factory.create_ticket(employee, title=f"DB count one {data_factory.run_id}")
    data_factory.create_ticket(employee, title=f"DB count two {data_factory.run_id}")
    other = data_factory.create_user("employee")
    data_factory.create_ticket(other, title=f"DB count other {data_factory.run_id}")

    response = employee.api.list_tickets(
        keyword=data_factory.run_id,
        page_size=100,
    )

    assert response.status_code == 200
    db_count = db_client.scalar(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE created_by = :user_id
          AND title ILIKE :keyword
        """,
        {
            "user_id": employee.id,
            "keyword": f"%{data_factory.run_id}%",
        },
    )
    assert response.json()["total"] == db_count == 2


def test_invalid_transition_leaves_ticket_and_audit_trail_unchanged(
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Transition consistency")
    before_ticket = db_client.fetch_one(
        "SELECT status, updated_at FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    before_events = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )

    response = employee.api.update_ticket_status(ticket["id"], "resolved")

    assert_error(response, 409)
    after_ticket = db_client.fetch_one(
        "SELECT status, updated_at FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    after_events = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert after_ticket == before_ticket
    assert after_events == before_events


def test_ticket_delete_cascades_audit_events(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Cascade check")
    data_factory.assign_ticket(ticket["id"], technician)
    assert (
        technician.api.update_ticket_status(ticket["id"], "in_progress").status_code
        == 200
    )

    response = admin_actor.api.delete_ticket(ticket["id"])

    assert response.status_code == 204
    assert (
        db_client.scalar(
            "SELECT COUNT(*) FROM tickets WHERE id = :ticket_id",
            {"ticket_id": ticket["id"]},
        )
        == 0
    )
    assert (
        db_client.scalar(
            "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
            {"ticket_id": ticket["id"]},
        )
        == 0
    )
