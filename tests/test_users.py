import uuid

import pytest

from tests.framework.api_client import ApiClient
from tests.framework.assertions import assert_error, assert_pagination
from tests.framework.db_client import DatabaseClient
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def _unique_user_payload(role: str = "employee") -> dict:
    suffix = uuid.uuid4().hex[:12]
    return {
        "username": f"usr_{suffix}",
        "email": f"usr_{suffix}@example.com",
        "password": "ValidPass123!",
        "role": role,
    }


def test_admin_can_create_user_and_database_stores_hashed_password(
    admin_actor: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    payload = _unique_user_payload()

    response = admin_actor.api.create_user(payload)

    assert response.status_code == 201
    body = response.json()
    data_factory.created_user_ids.append(body["id"])
    assert body["username"] == payload["username"]
    assert body["role"] == "employee"
    assert "password" not in body

    row = db_client.fetch_one(
        """
        SELECT id, username, email, role, is_active, password_hash
        FROM users
        WHERE id = :user_id
        """,
        {"user_id": body["id"]},
    )
    assert row is not None
    assert row["role"] == "employee"
    assert row["is_active"] is True
    assert row["password_hash"] != payload["password"]
    assert row["password_hash"].startswith("pbkdf2_sha256$")


def test_duplicate_username_returns_conflict_without_extra_db_row(
    admin_actor: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    payload = _unique_user_payload()
    created = admin_actor.api.create_user(payload)
    assert created.status_code == 201
    data_factory.created_user_ids.append(created.json()["id"])

    duplicate = {**payload, "email": f"another_{uuid.uuid4().hex[:8]}@example.com"}
    response = admin_actor.api.create_user(duplicate)

    assert_error(response, 409, "already exists")
    count = db_client.scalar(
        "SELECT COUNT(*) FROM users WHERE username = :username",
        {"username": payload["username"]},
    )
    assert count == 1


def test_duplicate_email_is_case_insensitive(
    admin_actor: Actor,
    data_factory: DataFactory,
) -> None:
    payload = _unique_user_payload()
    created = admin_actor.api.create_user(payload)
    assert created.status_code == 201
    data_factory.created_user_ids.append(created.json()["id"])

    duplicate = {
        **_unique_user_payload(),
        "email": payload["email"].upper(),
    }
    response = admin_actor.api.create_user(duplicate)

    assert_error(response, 409, "already exists")


@pytest.mark.parametrize("role", ["manager", "root", ""])
def test_create_user_rejects_unknown_role(
    admin_actor: Actor,
    role: str,
) -> None:
    payload = _unique_user_payload()
    payload["role"] = role

    response = admin_actor.api.create_user(payload)

    assert response.status_code == 422


def test_create_user_rejects_invalid_email(admin_actor: Actor) -> None:
    payload = _unique_user_payload()
    payload["email"] = "not-an-email"

    response = admin_actor.api.create_user(payload)

    assert response.status_code == 422


def test_employee_cannot_create_user(employee: Actor) -> None:
    response = employee.api.create_user(_unique_user_payload())

    assert_error(response, 403, "insufficient permissions")


def test_anonymous_user_cannot_create_user(anonymous_api: ApiClient) -> None:
    response = anonymous_api.create_user(_unique_user_payload())

    assert_error(response, 401, "authentication required")


def test_admin_user_list_supports_pagination(
    admin_actor: Actor,
    data_factory: DataFactory,
) -> None:
    for _ in range(3):
        data_factory.create_user("employee")

    response = admin_actor.api.list_users(
        page=1,
        page_size=2,
        keyword=data_factory.run_id,
    )

    assert response.status_code == 200
    body = response.json()
    assert_pagination(body, page=1, page_size=2)
    assert body["total"] >= 3
    assert len(body["items"]) == 2


def test_admin_user_list_filters_by_role_and_keyword(
    admin_actor: Actor,
    data_factory: DataFactory,
) -> None:
    data_factory.create_user("employee")
    technician = data_factory.create_user("technician")

    response = admin_actor.api.list_users(
        role="technician",
        keyword=data_factory.run_id,
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == technician.id
    assert body["items"][0]["role"] == "technician"


@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({"page": 0}, 422),
        ({"page_size": 101}, 422),
        ({"page_size": 0}, 422),
    ],
)
def test_user_pagination_parameters_are_bounded(
    admin_actor: Actor,
    params: dict,
    expected_status: int,
) -> None:
    response = admin_actor.api.list_users(**params)

    assert response.status_code == expected_status


def test_user_can_read_self_but_not_another_user(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    other = data_factory.create_user("employee")

    self_response = employee.api.get_user(employee.id)
    other_response = employee.api.get_user(other.id)

    assert self_response.status_code == 200
    assert self_response.json()["id"] == employee.id
    assert_error(other_response, 404, "not found")


def test_employee_cannot_list_users(employee: Actor) -> None:
    response = employee.api.list_users()

    assert_error(response, 403, "insufficient permissions")


def test_admin_can_change_role_and_database_is_updated(
    admin_actor: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    user = data_factory.create_user("employee")

    response = admin_actor.api.update_user_role(user.id, "technician")

    assert response.status_code == 200
    assert response.json()["role"] == "technician"
    row = db_client.fetch_one(
        "SELECT role FROM users WHERE id = :user_id",
        {"user_id": user.id},
    )
    assert row is not None
    assert row["role"] == "technician"


def test_employee_cannot_change_user_role(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    target = data_factory.create_user("employee")

    response = employee.api.update_user_role(target.id, "admin")

    assert_error(response, 403, "insufficient permissions")


def test_admin_can_deactivate_another_user(
    admin_actor: Actor,
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    user = data_factory.create_user("employee")

    response = admin_actor.api.update_user_active(user.id, False)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    row = db_client.fetch_one(
        "SELECT is_active FROM users WHERE id = :user_id",
        {"user_id": user.id},
    )
    assert row is not None
    assert row["is_active"] is False


def test_admin_cannot_deactivate_current_account(admin_actor: Actor) -> None:
    response = admin_actor.api.update_user_active(admin_actor.id, False)

    assert_error(response, 409, "cannot deactivate")


def test_admin_cannot_demote_current_account(
    data_factory: DataFactory,
    db_client: DatabaseClient,
) -> None:
    temporary_admin = data_factory.create_user("admin")

    response = temporary_admin.api.update_user_role(
        temporary_admin.id,
        "employee",
    )

    assert_error(response, 409, "cannot demote")
    row = db_client.fetch_one(
        "SELECT role FROM users WHERE id = :user_id",
        {"user_id": temporary_admin.id},
    )
    assert row == {"role": "admin"}
