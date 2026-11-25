import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TestConfig:
    __test__ = False

    api_base_url: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    admin_username: str
    admin_password: str
    admin_email: str
    request_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> "TestConfig":
        return cls(
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
            database_url=os.getenv(
                "DATABASE_URL",
                (
                    "postgresql+psycopg://service_desk:service_desk"
                    "@localhost:5432/service_desk"
                ),
            ),
            jwt_secret=os.getenv(
                "JWT_SECRET",
                "local-dev-secret-change-me-32-bytes-minimum",
            ),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password=os.getenv("ADMIN_PASSWORD", "Admin123!"),
            admin_email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "5")),
        )
