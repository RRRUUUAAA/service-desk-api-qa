import logging
import time
from typing import Any

import requests

from tests.framework.config import TestConfig


logger = logging.getLogger("tests.http")


class ApiClient:
    def __init__(self, config: TestConfig, token: str | None = None):
        self.config = config
        self.base_url = config.api_base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.set_token(token)

    def set_token(self, token: str | None) -> None:
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        started_at = time.perf_counter()
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                params=params,
                timeout=self.config.request_timeout,
            )
        except requests.RequestException:
            logger.exception("%s %s request failed", method.upper(), path)
            raise
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            method.upper(),
            path,
            response.status_code,
            elapsed_ms,
        )
        return response

    def health(self) -> requests.Response:
        return self.request("GET", "/health")

    def login(self, username: str, password: str) -> requests.Response:
        return self.request(
            "POST",
            "/auth/login",
            json={"username": username, "password": password},
        )

    def me(self) -> requests.Response:
        return self.request("GET", "/auth/me")

    def create_user(self, payload: dict[str, Any]) -> requests.Response:
        return self.request("POST", "/users", json=payload)

    def list_users(self, **params: Any) -> requests.Response:
        return self.request(
            "GET",
            "/users",
            params={key: value for key, value in params.items() if value is not None},
        )

    def get_user(self, user_id: int) -> requests.Response:
        return self.request("GET", f"/users/{user_id}")

    def update_user_role(self, user_id: int, role: str) -> requests.Response:
        return self.request(
            "PATCH",
            f"/users/{user_id}/role",
            json={"role": role},
        )

    def update_user_active(self, user_id: int, is_active: bool) -> requests.Response:
        return self.request(
            "PATCH",
            f"/users/{user_id}/active",
            json={"is_active": is_active},
        )

    def create_ticket(self, payload: dict[str, Any]) -> requests.Response:
        return self.request("POST", "/tickets", json=payload)

    def list_tickets(self, **params: Any) -> requests.Response:
        return self.request(
            "GET",
            "/tickets",
            params={key: value for key, value in params.items() if value is not None},
        )

    def get_ticket(self, ticket_id: int) -> requests.Response:
        return self.request("GET", f"/tickets/{ticket_id}")

    def update_ticket(
        self, ticket_id: int, payload: dict[str, Any]
    ) -> requests.Response:
        return self.request("PATCH", f"/tickets/{ticket_id}", json=payload)

    def delete_ticket(self, ticket_id: int) -> requests.Response:
        return self.request("DELETE", f"/tickets/{ticket_id}")

    def assign_ticket(
        self, ticket_id: int, assignee_id: int
    ) -> requests.Response:
        return self.request(
            "POST",
            f"/tickets/{ticket_id}/assign",
            json={"assignee_id": assignee_id},
        )

    def update_ticket_status(
        self, ticket_id: int, ticket_status: str
    ) -> requests.Response:
        return self.request(
            "PATCH",
            f"/tickets/{ticket_id}/status",
            json={"status": ticket_status},
        )
