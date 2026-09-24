"""Server-only model configuration in Airflow's encrypted connection store.

This module's SQLAlchemy access is for the Airflow-hosted web plugin, never a DAG
worker. LLM tasks resolve the same connection through the supported provider hook.
"""
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import workflow
from .store import transaction

CONNECTION_ID = "retcon_openrouter"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"

# An explicit harmless credential stops the OpenAI client inheriting a cloud key
# from OPENAI_API_KEY when a local server does not require authentication.
LOCAL_NO_KEY = "retcon-local-no-key"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def default_base_url():
    return "http://host.docker.internal:1234/v1" if Path("/.dockerenv").exists() else DEFAULT_BASE_URL


def normalize_model(value, provider="openrouter"):
    value = value.strip()
    prefix = "openrouter:" if provider == "openrouter" else "openai-chat:"
    if value.startswith(prefix):
        value = value[len(prefix):]
    if not re.fullmatch(r"[A-Za-z0-9_.:/-]{3,160}", value) or (provider == "openrouter" and "/" not in value):
        if provider == "openrouter":
            raise ValueError("Enter an OpenRouter model ID, such as google/gemma-4-31b-it:free.")
        raise ValueError("Enter the model ID shown by your OpenAI-compatible server.")
    return value


def normalize_base_url(value):
    value = (value or default_base_url()).strip().rstrip("/")
    try:
        url = urlsplit(value)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username is not None
                or url.password is not None or url.query or url.fragment
                or re.search(r"[\s\\]", value) or len(value) > 2000):
            raise ValueError
        port = url.port  # Validate ports before storing or making an HTTP request.
        host = url.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        if port is not None and port != (443 if url.scheme == "https" else 80):
            host += f":{port}"
        return urlunsplit((url.scheme, host, url.path.rstrip("/"), "", ""))
    except ValueError:
        raise ValueError("Enter an HTTP(S) API base URL without credentials, query, or fragment; include /v1 for LM Studio.") from None


def _target(model, provider, base_url):
    if provider not in {"openrouter", "openai"}:
        raise ValueError("Choose OpenRouter or an OpenAI-compatible provider.")
    return {"model": normalize_model(model, provider), "provider": provider,
            "base_url": normalize_base_url(base_url) if provider == "openai" else None}


def _connection_settings(connection):
    if not connection:
        return {"model": DEFAULT_MODEL, "provider": "openrouter", "base_url": None, "key": None}
    stored_model = connection.extra_dejson.get("model", "openrouter:" + DEFAULT_MODEL)
    provider = "openai" if stored_model.startswith("openai-chat:") else "openrouter"
    current = _target(stored_model, provider, getattr(connection, "host", None))
    current["key"] = connection.password
    if provider == "openai" and current["key"] == LOCAL_NO_KEY:
        current["key"] = None
    return current


def _database_credentials():
    from airflow.models.connection import Connection
    from airflow.utils.session import create_session
    from sqlalchemy import select

    with create_session() as session:
        connection = session.scalar(select(Connection).where(Connection.conn_id == CONNECTION_ID))
        return _connection_settings(connection)


def public_settings():
    saved = _database_credentials()
    current = workflow.load_state()
    override = bool(os.getenv("AIRFLOW_CONN_RETCON_OPENROUTER"))
    active = bool(current.get("run") and current["run"]["status"] in workflow.ACTIVE)
    return {"configured": bool(saved["key"]) or saved["provider"] == "openai",
            "model": saved["model"], "provider": saved["provider"], "base_url": saved["base_url"],
            "default_base_url": default_base_url(),
            "key_present": bool(saved["key"]), "editable": not active and not override,
            "connection_id": CONNECTION_ID,
            "message": "Remove the environment connection override and restart Airflow to edit here." if override else
                       "Finish or cancel the active revision before changing its model." if active else ""}


def _selected_key(api_key, target, saved):
    key = api_key.strip() if api_key else None
    if not key and (target["provider"], target["base_url"]) == (saved["provider"], saved["base_url"]):
        key = saved["key"]
    if key and re.search(r"[^!-~]", key):
        raise ValueError("Enter a valid API key without whitespace or special characters.")
    if target["provider"] == "openrouter":
        if not key:
            raise ValueError("Enter an OpenRouter API key to finish setup.")
        if not key.startswith("sk-or-") or len(key) < 20:
            raise ValueError("Enter a valid OpenRouter API key.")
    return key


def save_settings(model, api_key=None, provider="openrouter", base_url=None):
    from airflow.configuration import conf
    from airflow.models.connection import Connection
    from airflow.utils.session import create_session
    from sqlalchemy import select

    target = _target(model, provider, base_url)
    if os.getenv("AIRFLOW_CONN_RETCON_OPENROUTER"):
        raise ValueError("An environment connection overrides the UI. Remove it and restart Airflow first.")
    with transaction() as state:
        workflow.ensure_editable(state)
        with create_session() as session:
            connection = session.scalar(select(Connection).where(Connection.conn_id == CONNECTION_ID))
            key = _selected_key(api_key, target, _connection_settings(connection))
            if key and not conf.get("core", "fernet_key"):
                raise ValueError("Configure Airflow's Fernet key before saving a provider credential.")
            if not connection:
                connection = Connection(conn_id=CONNECTION_ID, conn_type="pydanticai")
                session.add(connection)
            connection.password = key or LOCAL_NO_KEY
            connection.conn_type = "pydanticai"
            connection.host = target["base_url"]
            prefix = "openrouter:" if provider == "openrouter" else "openai-chat:"
            connection.extra = json.dumps({"model": prefix + target["model"]})
            connection.description = "RETCON writer: model endpoint and API credential"
    return public_settings()


def test_settings(model, api_key=None, provider="openrouter", base_url=None):
    target = _target(model, provider, base_url)
    api_key = _selected_key(api_key, target, _database_credentials())
    model = target["model"]
    label = "OpenRouter" if provider == "openrouter" else "The model server"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    body = {"model": model, "messages": [{"role": "user", "content": "Reply with exactly: RETCON READY"}],
            "max_tokens": 256, "temperature": 0}
    if provider == "openrouter":
        headers["X-Title"] = "RETCON Airflow Plugin"
        body["reasoning"] = {"enabled": False}
    try:
        response = httpx.post((target["base_url"] or OPENROUTER_BASE_URL) + "/chat/completions",
                              headers=headers, json=body, timeout=90)
    except httpx.HTTPError:
        return {"ok": False, "message": f"{label} could not be reached. Check the server and base URL, then try again.", "model": model}
    if response.status_code != 200:
        message = {401: f"{label} rejected this API key.", 402: "This account has insufficient model credits.",
                   403: "This key is not allowed to use this model.", 404: f"{label} could not find this model or API endpoint.",
                   429: f"{label} rate limit reached. Try again later."}.get(
                       response.status_code, "The model provider is temporarily unavailable. Try again shortly.")
        return {"ok": False, "message": message, "model": model}
    try:
        choice = response.json()["choices"][0]
        ok = choice.get("finish_reason") == "stop" and bool(choice.get("message", {}).get("content"))
    except (KeyError, IndexError, ValueError, TypeError):
        ok = False
    return {"ok": ok, "message": "Connected. The selected model returned a real response." if ok else
            "The provider returned an incomplete response. Try again shortly.", "model": model}
