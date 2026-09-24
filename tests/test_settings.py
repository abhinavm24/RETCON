"""Provider setup contract without real credentials, provider calls, or a metadata DB."""

from contextlib import contextmanager
from copy import deepcopy
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, create_autospec

from fastapi.testclient import TestClient
import httpx
import pytest

from retcon import settings, store, webapp, workflow
from retcon.airflow_client import AirflowClient

FIXTURE_KEY = "sk-or-fixture-only-never-a-real-key"


@pytest.fixture
def connection_store(monkeypatch, tmp_path):
    """Replace only the database boundary; retain the real settings behavior."""
    monkeypatch.setattr(store, "STATE_DIR", tmp_path / "state")
    monkeypatch.delenv("AIRFLOW_CONN_RETCON_OPENROUTER", raising=False)

    class Connection:
        conn_id = "conn_id"

        def __init__(self, conn_id, conn_type):
            self.conn_id = conn_id
            self.conn_type = conn_type
            self.password = None
            self.extra = "{}"

        @property
        def extra_dejson(self):
            return json.loads(self.extra)

    database = SimpleNamespace(connection=None)

    @contextmanager
    def create_session():
        # Changes commit only when the context exits successfully, like Airflow's session.
        session = SimpleNamespace(connection=deepcopy(database.connection))
        session.scalar = lambda query: session.connection
        session.add = lambda connection: setattr(session, "connection", connection)
        yield session
        database.connection = session.connection

    conf = Mock()
    conf.get.return_value = "fixture-fernet-configuration"
    database.conf = conf
    for name, attributes in {
        "airflow.configuration": {"conf": conf},
        "airflow.models.connection": {"Connection": Connection},
        "airflow.utils.session": {"create_session": create_session},
        "sqlalchemy": {"select": lambda model: SimpleNamespace(where=lambda condition: object())},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    return database


@pytest.fixture
def plugin_client(connection_store, monkeypatch):
    backend = create_autospec(AirflowClient, instance=True)
    backend.healthy.return_value = True
    backend.trigger.side_effect = lambda run_id: {"dag_run_id": "retcon__" + run_id}
    monkeypatch.setattr(webapp, "airflow", backend)
    with TestClient(webapp.app) as client:
        yield client, backend


def configure(client, model=settings.DEFAULT_MODEL, key=FIXTURE_KEY):
    return client.put("/api/settings", json={"model": model, "api_key": key})


def retcon_body():
    return {"character_id": "mara", "death_chapter": 2, "instruction": "Mara dies at the airlock."}


def test_setup_saves_server_side_connection_and_never_returns_the_key(plugin_client, connection_store):
    client, _ = plugin_client
    initial = client.get("/api/settings")
    assert initial.json()["configured"] is False
    response = configure(client)
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["key_present"] is True
    connection = connection_store.connection
    assert connection.conn_id == "retcon_openrouter"
    assert connection.conn_type == "pydanticai"
    assert connection.password == FIXTURE_KEY
    assert connection.extra_dejson == {"model": "openrouter:" + settings.DEFAULT_MODEL}
    for public_response in (response, client.get("/api/settings"), client.get("/api/state")):
        assert FIXTURE_KEY not in public_response.text
        assert "api_key" not in public_response.text
        assert "password" not in public_response.text


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_key_preserves_stored_credential_while_changing_model(plugin_client, connection_store, blank):
    client, _ = plugin_client
    assert configure(client).status_code == 200
    response = configure(client, model="openrouter:vendor/another-model:free", key=blank)
    assert response.status_code == 200
    assert response.json()["model"] == "vendor/another-model:free"
    assert connection_store.connection.password == FIXTURE_KEY
    assert connection_store.connection.extra_dejson["model"] == "openrouter:vendor/another-model:free"


@pytest.mark.parametrize("status", sorted(workflow.ACTIVE))
def test_model_changes_are_locked_for_an_active_revision(plugin_client, connection_store, status):
    client, _ = plugin_client
    configure(client)
    run = workflow.start_retcon(**retcon_body())
    workflow.annotate_run(run["id"], status=status)
    response = configure(client, model="vendor/different-model", key="sk-or-second-fixture-credential")
    assert response.status_code == 409
    assert connection_store.connection.password == FIXTURE_KEY
    assert connection_store.connection.extra_dejson["model"] == "openrouter:" + settings.DEFAULT_MODEL
    assert client.get("/api/settings").json()["editable"] is False


def test_missing_first_key_blocks_setup_and_a_revision_without_mutation(plugin_client, connection_store):
    client, backend = plugin_client
    before = store.load_state()
    missing = configure(client, key="")
    assert missing.status_code == 409
    assert connection_store.connection is None
    started = client.post("/api/retcons", json=retcon_body())
    assert started.status_code == 409
    assert "Settings" in started.json()["detail"]
    assert store.load_state() == before
    backend.trigger.assert_not_called()


def test_missing_fernet_configuration_prevents_credential_storage(plugin_client, connection_store):
    client, _ = plugin_client
    connection_store.conf.get.return_value = ""
    response = configure(client)
    assert response.status_code == 409
    assert "Fernet" in response.json()["detail"]
    assert connection_store.connection is None


def test_environment_override_disables_edits_instead_of_pretending_they_take_effect(plugin_client, monkeypatch):
    client, _ = plugin_client
    configure(client)
    monkeypatch.setenv("AIRFLOW_CONN_RETCON_OPENROUTER", "fixture-environment-override")
    assert client.get("/api/settings").json()["editable"] is False
    response = configure(client, model="vendor/another-model")
    assert response.status_code == 409
    assert "override" in response.json()["detail"]


def test_reported_model_tracks_saved_connection_and_setup_enables_a_revision(plugin_client):
    client, backend = plugin_client
    response = configure(client, model="  openrouter:vendor/selected-model:free  ")
    assert response.status_code == 200
    state = client.get("/api/state").json()
    assert state["engine"]["model"] == "vendor/selected-model:free"
    assert state["engine"]["available"] is True
    started = client.post("/api/retcons", json=retcon_body())
    assert started.status_code == 202
    backend.trigger.assert_called_once_with(started.json()["id"])


@pytest.mark.parametrize("status", [401, 402, 403, 404, 429, 500])
def test_provider_errors_are_sanitized_and_do_not_echo_credentials(plugin_client, monkeypatch, status):
    client, _ = plugin_client
    provider = Mock(return_value=httpx.Response(status, json={"error": f"Sensitive provider echo: {FIXTURE_KEY}"}))
    monkeypatch.setattr(settings.httpx, "post", provider)
    response = client.post("/api/settings/test", json={"model": settings.DEFAULT_MODEL, "api_key": FIXTURE_KEY})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert FIXTURE_KEY not in response.text
    assert "Sensitive provider echo" not in response.text


def test_provider_network_errors_are_sanitized(plugin_client, monkeypatch):
    client, _ = plugin_client
    provider = Mock(side_effect=httpx.ConnectError(f"Connection failure with {FIXTURE_KEY}"))
    monkeypatch.setattr(settings.httpx, "post", provider)
    response = client.post("/api/settings/test", json={"model": settings.DEFAULT_MODEL, "api_key": FIXTURE_KEY})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert FIXTURE_KEY not in response.text


def test_connection_test_uses_retained_key_and_requires_a_complete_model_response(plugin_client, monkeypatch):
    client, _ = plugin_client
    configure(client)
    provider = Mock(return_value=httpx.Response(200, json={
        "choices": [{"finish_reason": "stop", "message": {"content": "RETCON READY"}}]
    }))
    monkeypatch.setattr(settings.httpx, "post", provider)
    response = client.post("/api/settings/test", json={"model": "openrouter:vendor/test-model", "api_key": ""})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert provider.call_args.kwargs["headers"]["Authorization"] == "Bearer " + FIXTURE_KEY
    assert provider.call_args.kwargs["json"]["model"] == "vendor/test-model"
    provider.return_value = httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {}}]})
    incomplete = client.post("/api/settings/test", json={"model": "vendor/test-model"})
    assert incomplete.json()["ok"] is False


def test_validation_errors_never_echo_submitted_credentials(plugin_client):
    client, _ = plugin_client
    secret_like_input = FIXTURE_KEY * 30
    for path, method in (("/api/settings", client.put), ("/api/settings/test", client.post)):
        response = method(path, json={"model": settings.DEFAULT_MODEL, "api_key": secret_like_input})
        assert response.status_code == 422
        assert FIXTURE_KEY not in response.text
        assert "input" not in response.text


def test_environment_key_cannot_bypass_airflow_connection_setup(plugin_client, monkeypatch):
    client, backend = plugin_client
    monkeypatch.setenv("OPENROUTER_API_KEY", FIXTURE_KEY)
    current = client.get("/api/settings")
    assert current.status_code == 200
    assert current.json()["editable"] is True
    assert current.json()["configured"] is False
    assert current.json()["key_present"] is False
    assert FIXTURE_KEY not in current.text
    before = store.load_state()
    response = client.post("/api/retcons", json=retcon_body())
    assert response.status_code == 409
    assert "Settings" in response.json()["detail"]
    assert store.load_state() == before
    backend.trigger.assert_not_called()


@pytest.mark.parametrize("model", ["google", "google/model with spaces", "https://invalid model", "vendor/model\nextra"])
def test_invalid_model_names_are_rejected_without_revealing_a_key(plugin_client, model):
    client, _ = plugin_client
    response = configure(client, model=model)
    assert response.status_code == 409
    assert FIXTURE_KEY not in response.text


LOCAL_MODEL = "qwen3.8-27b-uncensored-mlx"
LOCAL_URL = "http://127.0.0.1:1234/v1"


def local_body(**updates):
    return {"provider": "openai", "model": LOCAL_MODEL, "base_url": LOCAL_URL, **updates}


def successful_provider(monkeypatch):
    provider = Mock(return_value=httpx.Response(200, json={
        "choices": [{"finish_reason": "stop", "message": {"content": "RETCON READY"}}]
    }))
    monkeypatch.setattr(settings.httpx, "post", provider)
    return provider


def test_keyless_local_setup_saves_native_chat_connection_and_enables_revision(plugin_client, connection_store):
    client, backend = plugin_client
    connection_store.conf.get.return_value = ""
    response = client.put("/api/settings", json=local_body())
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["key_present"] is False
    assert response.json()["provider"] == "openai"
    assert response.json()["model"] == LOCAL_MODEL
    assert response.json()["base_url"] == LOCAL_URL
    assert connection_store.connection.host == LOCAL_URL
    assert connection_store.connection.extra_dejson == {"model": "openai-chat:" + LOCAL_MODEL}
    assert connection_store.connection.password == settings.LOCAL_NO_KEY
    assert settings.LOCAL_NO_KEY not in response.text
    started = client.post("/api/retcons", json=retcon_body())
    assert started.status_code == 202
    backend.trigger.assert_called_once_with(started.json()["id"])


def test_switch_to_local_never_sends_or_retains_openrouter_key(plugin_client, connection_store, monkeypatch):
    client, _ = plugin_client
    configure(client)
    provider = successful_provider(monkeypatch)
    tested = client.post("/api/settings/test", json=local_body(api_key=""))
    assert tested.json()["ok"] is True
    assert provider.call_args.args == (LOCAL_URL + "/chat/completions",)
    assert "Authorization" not in provider.call_args.kwargs["headers"]
    assert "X-Title" not in provider.call_args.kwargs["headers"]
    assert "reasoning" not in provider.call_args.kwargs["json"]
    assert FIXTURE_KEY not in str(provider.call_args)
    # Testing unsaved settings leaves the current connection intact.
    assert connection_store.connection.password == FIXTURE_KEY
    saved = client.put("/api/settings", json=local_body(api_key=""))
    assert saved.status_code == 200
    assert connection_store.connection.password == settings.LOCAL_NO_KEY
    assert saved.json()["key_present"] is False
    assert configure(client, key="").status_code == 409
    assert connection_store.connection.extra_dejson["model"] == "openai-chat:" + LOCAL_MODEL


def test_local_endpoint_key_is_reused_only_for_same_normalized_endpoint(plugin_client, connection_store, monkeypatch):
    client, _ = plugin_client
    key = "fixture-local-server-token"
    assert client.put("/api/settings", json=local_body(api_key=key)).status_code == 200
    provider = successful_provider(monkeypatch)
    same = client.post("/api/settings/test", json=local_body(base_url=LOCAL_URL + "/", api_key=" "))
    assert same.json()["ok"] is True
    assert provider.call_args.kwargs["headers"]["Authorization"] == "Bearer " + key
    changed = client.post("/api/settings/test", json=local_body(base_url="http://localhost:2345/v1"))
    assert changed.json()["ok"] is True
    assert "Authorization" not in provider.call_args.kwargs["headers"]
    saved = client.put("/api/settings", json=local_body(base_url="http://localhost:2345/v1"))
    assert saved.status_code == 200
    assert saved.json()["key_present"] is False
    assert connection_store.connection.password == settings.LOCAL_NO_KEY


def test_local_api_key_requires_encrypted_storage_and_is_never_returned(plugin_client, connection_store):
    client, _ = plugin_client
    key = "fixture-local-server-token"
    connection_store.conf.get.return_value = ""
    assert client.put("/api/settings", json=local_body(api_key=key)).status_code == 409
    assert connection_store.connection is None
    connection_store.conf.get.return_value = "fixture-fernet"
    saved = client.put("/api/settings", json=local_body(api_key=key))
    assert saved.status_code == 200
    assert saved.json()["key_present"] is True
    assert key not in saved.text
    assert key not in client.get("/api/settings").text


@pytest.mark.parametrize("base_url", [
    "file:///tmp/socket", "ftp://127.0.0.1/v1", "http:///v1", "http://user:secret@localhost/v1",
    "http://localhost/v1?key=secret", "http://localhost/v1#secret", "http://localhost:invalid/v1",
    "http://local host/v1", "http://localhost\\example.com/v1",
])
def test_bad_endpoint_is_rejected_before_credentials_or_network_are_touched(plugin_client, connection_store, monkeypatch, base_url):
    client, _ = plugin_client
    configure(client)
    provider = successful_provider(monkeypatch)
    for path, method in (("/api/settings", client.put), ("/api/settings/test", client.post)):
        response = method(path, json=local_body(base_url=base_url))
        assert response.status_code == 409
        assert "secret" not in response.text
    assert connection_store.connection.password == FIXTURE_KEY
    provider.assert_not_called()


@pytest.mark.parametrize("base_url,expected", [
    (" HTTP://LOCALHOST:80/v1/ ", "http://localhost/v1"),
    ("https://EXAMPLE.COM:443/v1/", "https://example.com/v1"),
    ("http://[::1]:1234/v1/", "http://[::1]:1234/v1"),
])
def test_endpoint_normalization(base_url, expected):
    assert settings.normalize_base_url(base_url) == expected


def test_local_network_and_provider_errors_do_not_echo_keys_or_server_body(plugin_client, monkeypatch):
    client, _ = plugin_client
    secret = "fixture-local-server-token"
    provider = Mock(side_effect=httpx.ConnectError(secret))
    monkeypatch.setattr(settings.httpx, "post", provider)
    failed = client.post("/api/settings/test", json=local_body(api_key=secret))
    assert failed.status_code == 200
    assert failed.json()["ok"] is False
    assert secret not in failed.text
    provider.side_effect = None
    provider.return_value = httpx.Response(500, json={"error": "private-provider-body " + secret})
    failed = client.post("/api/settings/test", json=local_body(api_key=secret))
    assert failed.json()["ok"] is False
    assert secret not in failed.text
    assert "private-provider-body" not in failed.text


def test_local_settings_are_locked_for_active_revision(plugin_client, connection_store):
    client, _ = plugin_client
    configure(client)
    workflow.start_retcon(**retcon_body())
    response = client.put("/api/settings", json=local_body())
    assert response.status_code == 409
    assert connection_store.connection.password == FIXTURE_KEY
    assert connection_store.connection.extra_dejson["model"].startswith("openrouter:")
