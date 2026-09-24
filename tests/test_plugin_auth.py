"""Run with Airflow installed to check the plugin against the installed Airflow auth API."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from retcon.plugin_auth import AirflowSessionMiddleware, airflow_token

pytest.importorskip("airflow")


@pytest.fixture
def authenticated_plugin(monkeypatch):
    from airflow.api_fastapi import app as airflow_app
    from airflow.api_fastapi.core_api import security

    manager = Mock()
    manager.get_url_login.return_value = "/auth/login"
    user = object()

    async def resolve(token):
        if token != "writer-session":
            raise HTTPException(401, "Not authenticated")
        return user

    resolver = AsyncMock(side_effect=resolve)
    monkeypatch.setattr(security, "resolve_user_from_token", resolver)
    monkeypatch.setattr(airflow_app, "get_auth_manager", lambda: manager)
    app = FastAPI()
    app.add_middleware(AirflowSessionMiddleware)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT"])
    def route(path: str):
        # A synchronous FastAPI handler is executed in a worker thread. The
        # current user's token must survive that boundary for REST calls.
        return {"token": airflow_token.get()}

    with TestClient(app, follow_redirects=False) as client:
        yield client, manager, resolver


def test_anonymous_api_is_blocked_and_workspace_enters_airflow_login(authenticated_plugin):
    client, _, _ = authenticated_plugin
    assert client.get("/retcon/api/state").status_code == 401
    response = client.get("/retcon/")
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_cookie_auth_reaches_sync_handler_and_is_not_retained(authenticated_plugin):
    client, manager, _ = authenticated_plugin
    client.cookies.set("_token", "writer-session")
    response = client.get("/retcon/api/state")
    assert response.status_code == 200
    assert response.json() == {"token": "writer-session"}
    assert response.headers["cache-control"] == "no-store"
    assert airflow_token.get() is None
    client.cookies.clear()
    assert client.get("/retcon/api/state").status_code == 401


def test_bearer_session_supports_writes_without_custom_role_checks(authenticated_plugin):
    client, manager, resolver = authenticated_plugin
    response = client.put("/retcon/api/settings", headers={"Authorization": "Bearer writer-session"})
    assert response.status_code == 200
    assert response.json() == {"token": "writer-session"}
    resolver.assert_awaited_once_with("writer-session")
    manager.is_authorized_dag.assert_not_called()
    manager.is_authorized_connection.assert_not_called()
