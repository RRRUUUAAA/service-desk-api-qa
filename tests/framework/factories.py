import uuid
from dataclasses import dataclass
from typing import Any

from tests.framework.api_client import ApiClient
from tests.framework.config import TestConfig
from tests.framework.db_client import DatabaseClient


@dataclass
class Actor:
    id: int
    username: str
    email: str
    password: str
    role: str
    token: str
    api: ApiClient


class DataFactory:
    def __init__(
        self,
        config: TestConfig,
        admin_actor: Actor,
        db: DatabaseClient,
    ):
        self.config = config
        self.admin = admin_actor
        self.db = db
        self.run_id = uuid.uuid4().hex[:8]
        self._sequence = 0
        self.created_user_ids: list[int] = []
        self.created_ticket_ids: list[int] = []

    def _next_value(self, prefix: str) -> str:
        self._sequence += 1
        return f"{prefix}{self.run_id}{self._sequence:02d}"

    def create_user(
        self,
        role: str = "employee",
        *,
        active: bool = True,
    ) -> Actor:
        sequence = self._next_value("qa")
        username = f"{sequence}_{role}"[:32]
        email = f"{sequence}@example.com"
        password = "QaPass123!"
        response = self.admin.api.create_user(
            {
                "username": username,
                "email": email,
                "password": password,
                "role": role,
            }
        )
        if response.status_code != 201:
            raise AssertionError(
                f"Failed to create test user: {response.status_code} {response.text}"
            )

        user = response.json()
        self.created_user_ids.append(user["id"])
        if not active:
            deactivate = self.admin.api.update_user_active(user["id"], False)
            if deactivate.status_code != 200:
                raise AssertionError(
                    f"Failed to deactivate test user: {deactivate.text}"
                )

        token = ""
        if active:
            login_response = self.admin.api.login(username, password)
            if login_response.status_code != 200:
                raise AssertionError(
                    f"Failed to login test user: {login_response.text}"
                )
            token = login_response.json()["access_token"]

        return Actor(
            id=user["id"],
            username=username,
            email=email,
            password=password,
            role=role,
            token=token,
            api=ApiClient(self.config, token=token or None),
        )

    def create_ticket(
        self,
        actor: Actor,
        *,
        title: str | None = None,
        description: str = "",
        priority: str = "medium",
    ) -> dict[str, Any]:
        ticket_title = title or f"qa {self._next_value('ticket')}"
        response = actor.api.create_ticket(
            {
                "title": ticket_title,
                "description": description,
                "priority": priority,
            }
        )
        if response.status_code != 201:
            raise AssertionError(
                f"Failed to create test ticket: {response.status_code} {response.text}"
            )
        ticket = response.json()
        self.created_ticket_ids.append(ticket["id"])
        return ticket

    def assign_ticket(
        self,
        ticket_id: int,
        technician: Actor,
    ) -> dict[str, Any]:
        response = self.admin.api.assign_ticket(ticket_id, technician.id)
        if response.status_code != 200:
            raise AssertionError(
                f"Failed to assign test ticket: {response.status_code} {response.text}"
            )
        return response.json()

    def cleanup(self) -> None:
        self.db.cleanup(
            user_ids=self.created_user_ids,
            ticket_ids=self.created_ticket_ids,
        )
