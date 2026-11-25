from datetime import datetime, timedelta, timezone

import jwt
import pytest

from tests.framework.api_client import ApiClient
from tests.framework.assertions import assert_error
from tests.framework.config import TestConfig
from tests.framework.factories import Actor, DataFactory


pytestmark = pytest.mark.integration


def test_admin_can_login_and_receives_access_token(
    anonymous_api: ApiClient,
    test_config: TestConfig,
) -> None:
    response = anonymous_api.login(
        test_config.admin_username,
        test_config.admin_password,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["role"] == "admin"


def test_login_with_wrong_password_is_rejected(
    anonymous_api: ApiClient,
    test_config: TestConfig,
) -> None:
    response = anonymous_api.login(
        test_config.admin_username,
        "definitely-wrong-password",
    )

    assert_error(response, 401, "invalid username or password")
    assert "access_token" not in response.json()


def test_login_with_unknown_username_uses_same_generic_error(
    anonymous_api: ApiClient,
) -> None:
    response = anonymous_api.login("missing-user-for-qa", "WrongPass123!")

    assert_error(response, 401, "invalid username or password")


def test_login_without_password_fails_validation(
    anonymous_api: ApiClient,
    test_config: TestConfig,
) -> None:
    response = anonymous_api.request(
        "POST",
        "/auth/login",
        json={"username": test_config.admin_username},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_authenticated_user_can_read_own_profile(admin_actor: Actor) -> None:
    response = admin_actor.api.me()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == admin_actor.id
    assert body["username"] == admin_actor.username
    assert body["role"] == "admin"


def test_me_without_token_returns_401(anonymous_api: ApiClient) -> None:
    response = anonymous_api.me()

    assert_error(response, 401, "authentication required")
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_malformed_token_returns_401(
    anonymous_api: ApiClient,
    test_config: TestConfig,
) -> None:
    anonymous_api.set_token("not-a-valid-jwt")

    response = anonymous_api.me()

    assert_error(response, 401, "invalid or expired token")


def test_me_with_expired_token_returns_401(
    anonymous_api: ApiClient,
    test_config: TestConfig,
    admin_actor: Actor,
) -> None:
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": str(admin_actor.id),
            "role": admin_actor.role,
            "type": "access",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=1),
        },
        test_config.jwt_secret,
        algorithm=test_config.jwt_algorithm,
    )
    anonymous_api.set_token(expired)

    response = anonymous_api.me()

    assert_error(response, 401, "invalid or expired token")


def test_inactive_user_cannot_login(
    data_factory: DataFactory,
    anonymous_api: ApiClient,
) -> None:
    inactive_user = data_factory.create_user("employee", active=False)

    response = anonymous_api.login(inactive_user.username, inactive_user.password)

    assert_error(response, 403, "inactive")


def test_token_is_rejected_after_account_is_deactivated(
    data_factory: DataFactory,
    admin_actor: Actor,
) -> None:
    user = data_factory.create_user("employee")
    assert user.api.me().status_code == 200

    deactivate_response = admin_actor.api.update_user_active(user.id, False)
    assert deactivate_response.status_code == 200

    response = user.api.me()
    assert_error(response, 401, "inactive")
