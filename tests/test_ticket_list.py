import pytest

from tests.framework.api_client import ApiClient
from tests.framework.assertions import assert_error, assert_pagination
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def test_employee_list_only_contains_own_tickets(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    own_one = data_factory.create_ticket(employee, title=f"Own one {data_factory.run_id}")
    own_two = data_factory.create_ticket(employee, title=f"Own two {data_factory.run_id}")
    other = data_factory.create_user("employee")
    data_factory.create_ticket(other, title=f"Other {data_factory.run_id}")

    response = employee.api.list_tickets(
        keyword=data_factory.run_id,
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {own_one["id"], own_two["id"]}


def test_admin_list_contains_tickets_from_multiple_creators(
    admin_actor: Actor,
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    other = data_factory.create_user("employee")
    data_factory.create_ticket(employee, title=f"From employee {data_factory.run_id}")
    data_factory.create_ticket(other, title=f"From other {data_factory.run_id}")

    response = admin_actor.api.list_tickets(
        keyword=data_factory.run_id,
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["created_by"] for item in body["items"]} == {employee.id, other.id}


def test_technician_list_only_contains_assigned_tickets(
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    assigned = data_factory.create_ticket(
        employee,
        title=f"Assigned {data_factory.run_id}",
    )
    data_factory.create_ticket(
        employee,
        title=f"Not assigned {data_factory.run_id}",
    )
    data_factory.assign_ticket(assigned["id"], technician)

    response = technician.api.list_tickets(
        keyword=data_factory.run_id,
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == assigned["id"]
    assert body["items"][0]["assignee_id"] == technician.id


def test_list_filters_by_status(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    assigned = data_factory.create_ticket(
        employee,
        title=f"Assigned filter {data_factory.run_id}",
    )
    data_factory.create_ticket(
        employee,
        title=f"Open filter {data_factory.run_id}",
    )
    data_factory.assign_ticket(assigned["id"], technician)

    response = admin_actor.api.list_tickets(
        keyword=data_factory.run_id,
        status="assigned",
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == assigned["id"]
    assert body["items"][0]["status"] == "assigned"


def test_list_filters_by_priority(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    high = data_factory.create_ticket(
        employee,
        title=f"High priority {data_factory.run_id}",
        priority="high",
    )
    data_factory.create_ticket(
        employee,
        title=f"Low priority {data_factory.run_id}",
        priority="low",
    )

    response = employee.api.list_tickets(
        keyword=data_factory.run_id,
        priority="high",
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == high["id"]


def test_keyword_search_is_case_insensitive(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    ticket = data_factory.create_ticket(
        employee,
        title=f"PRINTER Jam {data_factory.run_id}",
        description="Paper is stuck in tray two",
    )

    response = employee.api.list_tickets(
        keyword="printer jam",
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == ticket["id"]


def test_ticket_pagination_returns_stable_descending_pages(
    employee: Actor,
    data_factory: DataFactory,
) -> None:
    created = [
        data_factory.create_ticket(
            employee,
            title=f"Page item {index} {data_factory.run_id}",
        )
        for index in range(3)
    ]

    first = employee.api.list_tickets(
        keyword=data_factory.run_id,
        page=1,
        page_size=2,
    )
    second = employee.api.list_tickets(
        keyword=data_factory.run_id,
        page=2,
        page_size=2,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert_pagination(first_body, page=1, page_size=2)
    assert_pagination(second_body, page=2, page_size=2)
    assert first_body["total"] == 3
    assert second_body["total"] == 3
    assert len(first_body["items"]) == 2
    assert len(second_body["items"]) == 1
    expected_ids = [ticket["id"] for ticket in reversed(created)]
    actual_ids = [
        item["id"]
        for item in first_body["items"] + second_body["items"]
    ]
    assert actual_ids == expected_ids


@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({"page": 0}, 422),
        ({"page_size": 0}, 422),
        ({"page_size": 101}, 422),
        ({"status": "unknown"}, 422),
    ],
)
def test_ticket_list_query_validation(
    employee: Actor,
    params: dict,
    expected_status: int,
) -> None:
    response = employee.api.list_tickets(**params)

    assert response.status_code == expected_status


def test_ticket_list_returns_empty_items_for_no_match(
    employee: Actor,
) -> None:
    response = employee.api.list_tickets(
        keyword="no-such-ticket-keyword-7f37d1",
        page_size=100,
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 100,
    }


def test_anonymous_user_cannot_list_tickets(anonymous_api: ApiClient) -> None:
    response = anonymous_api.list_tickets()

    assert_error(response, 401, "authentication required")


def test_admin_can_filter_by_assignee(
    admin_actor: Actor,
    employee: Actor,
    technician: Actor,
    data_factory: DataFactory,
) -> None:
    second_technician = data_factory.create_user("technician")
    first_ticket = data_factory.create_ticket(
        employee,
        title=f"Tech one {data_factory.run_id}",
    )
    second_ticket = data_factory.create_ticket(
        employee,
        title=f"Tech two {data_factory.run_id}",
    )
    data_factory.assign_ticket(first_ticket["id"], technician)
    data_factory.assign_ticket(second_ticket["id"], second_technician)

    response = admin_actor.api.list_tickets(
        keyword=data_factory.run_id,
        assignee_id=technician.id,
        page_size=100,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == first_ticket["id"]
