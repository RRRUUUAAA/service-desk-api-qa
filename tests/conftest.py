import time
from collections.abc import Generator

import pytest
import requests

from tests.framework.api_client import ApiClient
from tests.framework.config import TestConfig
from tests.framework.db_client import DatabaseClient
from tests.framework.factories import Actor, DataFactory


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    return TestConfig.from_env()


@pytest.fixture(scope="session")
def db_client(test_config: TestConfig) -> Generator[DatabaseClient, None, None]:
    client = DatabaseClient(test_config)
    yield client
    client.dispose()


def _wait_for_api(config: TestConfig, timeout_seconds: int = 30) -> None:
    client = ApiClient(config)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = client.health()
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(1)
    raise AssertionError(
        f"API did not become healthy within {timeout_seconds}s: {last_error}"
    )


@pytest.fixture(scope="session")
def admin_actor(test_config: TestConfig) -> Actor:
    _wait_for_api(test_config)
    anonymous = ApiClient(test_config)
    response = anonymous.login(
        test_config.admin_username,
        test_config.admin_password,
    )
    if response.status_code != 200:
        raise AssertionError(f"Admin login failed: {response.text}")
    token = response.json()["access_token"]
    user = response.json()["user"]
    return Actor(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        password=test_config.admin_password,
        role=user["role"],
        token=token,
        api=ApiClient(test_config, token=token),
    )


@pytest.fixture()
def anonymous_api(test_config: TestConfig) -> ApiClient:
    return ApiClient(test_config)


@pytest.fixture()
def data_factory(
    test_config: TestConfig,
    admin_actor: Actor,
    db_client: DatabaseClient,
) -> Generator[DataFactory, None, None]:
    factory = DataFactory(test_config, admin_actor, db_client)
    yield factory
    factory.cleanup()


@pytest.fixture()
def employee(data_factory: DataFactory) -> Actor:
    return data_factory.create_user("employee")


@pytest.fixture()
def technician(data_factory: DataFactory) -> Actor:
    return data_factory.create_user("technician")
