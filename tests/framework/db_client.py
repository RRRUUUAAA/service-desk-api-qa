from typing import Any

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

from tests.framework.config import TestConfig


class DatabaseClient:
    def __init__(self, config: TestConfig):
        self.engine: Engine = create_engine(
            config.database_url,
            pool_pre_ping=True,
        )

    def fetch_one(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(sql),
                params or {},
            ).mappings().one_or_none()
            return dict(row) if row is not None else None

    def fetch_all(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(sql),
                params or {},
            ).mappings().all()
            return [dict(row) for row in rows]

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(text(sql), params or {}).scalar()

    def cleanup(self, user_ids: list[int], ticket_ids: list[int]) -> None:
        if not ticket_ids and not user_ids:
            return

        with self.engine.begin() as connection:
            if ticket_ids:
                connection.execute(
                    text(
                        "DELETE FROM ticket_events "
                        "WHERE ticket_id IN :ticket_ids"
                    ).bindparams(
                        bindparam("ticket_ids", expanding=True)
                    ),
                    {"ticket_ids": ticket_ids},
                )
                connection.execute(
                    text(
                        "DELETE FROM tickets WHERE id IN :ticket_ids"
                    ).bindparams(
                        bindparam("ticket_ids", expanding=True)
                    ),
                    {"ticket_ids": ticket_ids},
                )
            if user_ids:
                connection.execute(
                    text(
                        "DELETE FROM users WHERE id IN :user_ids"
                    ).bindparams(
                        bindparam("user_ids", expanding=True)
                    ),
                    {"user_ids": user_ids},
                )

    def dispose(self) -> None:
        self.engine.dispose()
