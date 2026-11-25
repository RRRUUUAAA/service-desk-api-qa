import pytest

from tests.framework.assertions import assert_error
from tests.framework.db_client import DatabaseClient
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def _create_assigned_ticket(
    data_factory: DataFactory,
    employee: Actor,
    technician: Actor,
) -> dict:
    ticket = data_factory.create_ticket(
        employee,
        title=f"Workflow ticket {data_factory.run_id}",
    )
    return data_factory.assign_ticket(ticket["id"], technician)


def test_admin_can_assign_ticket_and_database_records_event(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Assign me")

    response = admin_actor.api.assign_ticket(ticket["id"], technician.id)

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] == technician.id
    assert body["status"] == "assigned"
    row = db_client.fetch_one(
        "SELECT assignee_id, status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"assignee_id": technician.id, "status": "assigned"}
    event = db_client.fetch_one(
        """
        SELECT actor_id, event_type, from_status, to_status
        FROM ticket_events
        WHERE ticket_id = :ticket_id
        ORDER BY id DESC
        LIMIT 1
        """,
        {"ticket_id": ticket["id"]},
    )
    assert event == {
        "actor_id": admin_actor.id,
        "event_type": "assigned",
        "from_status": "open",
        "to_status": "assigned",
    }


def test_duplicate_assignment_returns_conflict_without_partial_write(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    event_count_before = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )

    response = admin_actor.api.assign_ticket(ticket["id"], technician.id)

    assert_error(response, 409, "already assigned")
    event_count_after = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert event_count_after == event_count_before


def test_ticket_cannot_be_assigned_to_employee(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Wrong assignee role")
    another_employee = data_factory.create_user("employee")

    response = admin_actor.api.assign_ticket(ticket["id"], another_employee.id)

    assert_error(response, 409, "active technician")
    row = db_client.fetch_one(
        "SELECT assignee_id, status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"assignee_id": None, "status": "open"}


def test_assignment_to_unknown_user_returns_404(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Unknown assignee")

    response = admin_actor.api.assign_ticket(ticket["id"], 2_000_000_000)

    assert_error(response, 404, "assignee not found")


def test_assignment_to_inactive_technician_is_rejected(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    inactive_technician = data_factory.create_user("technician", active=False)
    ticket = data_factory.create_ticket(employee, title="Inactive technician")

    response = admin_actor.api.assign_ticket(
        ticket["id"],
        inactive_technician.id,
    )

    assert_error(response, 409, "active technician")


def test_employee_cannot_assign_ticket(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(employee, title="No assignment permission")

    response = employee.api.assign_ticket(ticket["id"], technician.id)

    assert_error(response, 403, "insufficient permissions")


def test_admin_can_reassign_active_ticket(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    second_technician = data_factory.create_user("technician")
    ticket = _create_assigned_ticket(data_factory, employee, technician)

    response = admin_actor.api.assign_ticket(ticket["id"], second_technician.id)

    assert response.status_code == 200
    assert response.json()["assignee_id"] == second_technician.id
    assert response.json()["status"] == "assigned"
    event = db_client.fetch_one(
        """
        SELECT event_type, from_status, to_status
        FROM ticket_events
        WHERE ticket_id = :ticket_id
        ORDER BY id DESC
        LIMIT 1
        """,
        {"ticket_id": ticket["id"]},
    )
    assert event == {
        "event_type": "reassigned",
        "from_status": "assigned",
        "to_status": "assigned",
    }


def test_assigned_technician_can_start_work(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)

    response = technician.api.update_ticket_status(ticket["id"], "in_progress")

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    row = db_client.fetch_one(
        "SELECT status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"status": "in_progress"}


def test_unassigned_technician_cannot_access_ticket(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    other_technician = data_factory.create_user("technician")
    ticket = _create_assigned_ticket(data_factory, employee, technician)

    response = other_technician.api.update_ticket_status(
        ticket["id"],
        "in_progress",
    )

    assert_error(response, 404, "ticket not found")


def test_creator_cannot_start_ticket_work(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)

    response = employee.api.update_ticket_status(ticket["id"], "in_progress")

    assert_error(response, 403, "insufficient permissions")


def test_assigned_technician_can_resolve_ticket(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    start = technician.api.update_ticket_status(ticket["id"], "in_progress")
    assert start.status_code == 200

    response = technician.api.update_ticket_status(ticket["id"], "resolved")

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    row = db_client.fetch_one(
        "SELECT status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"status": "resolved"}


def test_invalid_status_transition_does_not_change_database(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    event_count_before = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )

    response = technician.api.update_ticket_status(ticket["id"], "resolved")

    assert_error(response, 409, "invalid status transition")
    row = db_client.fetch_one(
        "SELECT status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    event_count_after = db_client.scalar(
        "SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"status": "assigned"}
    assert event_count_after == event_count_before


def test_creator_can_close_resolved_ticket(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    assert (
        technician.api.update_ticket_status(ticket["id"], "in_progress").status_code
        == 200
    )
    assert (
        technician.api.update_ticket_status(ticket["id"], "resolved").status_code
        == 200
    )

    response = employee.api.update_ticket_status(ticket["id"], "closed")

    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    row = db_client.fetch_one(
        "SELECT status FROM tickets WHERE id = :ticket_id",
        {"ticket_id": ticket["id"]},
    )
    assert row == {"status": "closed"}


def test_non_creator_cannot_close_resolved_ticket(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    assert (
        technician.api.update_ticket_status(ticket["id"], "in_progress").status_code
        == 200
    )
    assert (
        technician.api.update_ticket_status(ticket["id"], "resolved").status_code
        == 200
    )

    response = technician.api.update_ticket_status(ticket["id"], "closed")

    assert_error(response, 403, "insufficient permissions")


def test_creator_cannot_close_open_ticket_directly(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Cannot close directly")

    response = employee.api.update_ticket_status(ticket["id"], "closed")

    assert_error(response, 409, "invalid status transition")


@pytest.mark.parametrize("target_status", ["open", "assigned"])
def test_invalid_or_assignment_only_targets_are_rejected(
    employee: Actor,
    data_factory: DataFactory,
    target_status: str,
) -> None:
    ticket = data_factory.create_ticket(employee, title="Target validation")

    response = employee.api.update_ticket_status(ticket["id"], target_status)

    if target_status == "assigned":
        assert_error(response, 409, "assignment endpoint")
    else:
        assert_error(response, 409, "already has the requested status")


def test_ticket_cannot_be_assigned_after_work_started(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    second_technician = data_factory.create_user("technician")
    ticket = _create_assigned_ticket(data_factory, employee, technician)
    assert (
        technician.api.update_ticket_status(ticket["id"], "in_progress").status_code
        == 200
    )

    response = admin_actor.api.assign_ticket(
        ticket["id"],
        second_technician.id,
    )

    assert_error(response, 409, "only open or assigned")


def test_admin_can_drive_full_status_workflow(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = _create_assigned_ticket(data_factory, employee, technician)

    in_progress = admin_actor.api.update_ticket_status(
        ticket["id"], "in_progress"
    )
    resolved = admin_actor.api.update_ticket_status(ticket["id"], "resolved")
    closed = admin_actor.api.update_ticket_status(ticket["id"], "closed")

    assert in_progress.status_code == 200
    assert resolved.status_code == 200
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
