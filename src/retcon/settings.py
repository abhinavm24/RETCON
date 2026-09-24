"""Server-only OpenRouter configuration in Airflow's encrypted connection store.

This module's SQLAlchemy access is for the Airflow-hosted web plugin, never a DAG
worker. LLM tasks resolve the same connection through the supported provider hook.
"""
import json
import os
import re

import httpx

from . import workflow
from .store import transaction

CONNECTION_ID = "retcon_openrouter"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"


def normalize_model(value):
    value = value.strip()
    if value.startswith("openrouter:"):
        value = value[len("openrouter:"):]
    if not re.fullmatch(r"[A-Za-z0-9_.:/-]{3,160}", value) or "/" not in value:
        raise ValueError("Enter an OpenRouter model ID, such as google/gemma-4-31b-it:free.")
    return value


def _database_credentials():
    from airflow.models.connection import Connection
    from airflow.utils.session import create_session
    from sqlalchemy import select

    with create_session() as session:
        connection = session.scalar(select(Connection).where(Connection.conn_id == CONNECTION_ID))
        if not connection:
            return DEFAULT_MODEL, None
        model = connection.extra_dejson.get("model", "openrouter:" + DEFAULT_MODEL)
        return normalize_model(model), connection.password


def public_settings():
    model, key = _database_credentials()
    current = workflow.load_state()
    override = bool(os.getenv("AIRFLOW_CONN_RETCON_OPENROUTER"))
    active = bool(current.get("run") and current["run"]["status"] in workflow.ACTIVE)
    return {"configured": bool(key), "model": model, "provider": "OpenRouter", "key_present": bool(key),
            "editable": not active and not override, "connection_id": CONNECTION_ID,
            "message": "Remove the environment connection override and restart Airflow to edit here." if override else
                       "Finish or cancel the active revision before changing its model." if active else ""}


def save_settings(model, api_key=None):
    from airflow.configuration import conf
    from airflow.models.connection import Connection
    from airflow.utils.session import create_session
    from sqlalchemy import select

    model = normalize_model(model)
    if os.getenv("AIRFLOW_CONN_RETCON_OPENROUTER"):
        raise ValueError("An environment connection overrides the UI. Remove it and restart Airflow first.")
    if not conf.get("core", "fernet_key"):
        raise ValueError("Configure Airflow's Fernet key before saving a provider credential.")
    with transaction() as state:
        workflow.ensure_editable(state)
        with create_session() as session:
            connection = session.scalar(select(Connection).where(Connection.conn_id == CONNECTION_ID))
            if not connection:
                connection = Connection(conn_id=CONNECTION_ID, conn_type="pydanticai")
                session.add(connection)
            new_key = api_key.strip() if api_key else None
            if not new_key and not connection.password:
                raise ValueError("Enter an OpenRouter API key to finish setup.")
            if new_key:
                if not new_key.startswith("sk-or-") or len(new_key) < 20:
                    raise ValueError("Enter a valid OpenRouter API key.")
                connection.password = new_key
            connection.conn_type = "pydanticai"
            connection.host = None
            connection.extra = json.dumps({"model": "openrouter:" + model})
            connection.description = "RETCON writer: OpenRouter model and API credential"
    return public_settings()


def test_settings(model, api_key=None):
    model = normalize_model(model)
    if not api_key:
        _, api_key = _database_credentials()
    if not api_key:
        raise ValueError("Enter an API key before testing the connection.")
    try:
        response = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers={
            "Authorization": "Bearer " + api_key, "Content-Type": "application/json",
            "X-Title": "RETCON Airflow Plugin"}, json={
                "model": model, "messages": [{"role": "user", "content": "Reply with exactly: RETCON READY"}],
                "max_tokens": 48, "temperature": 0, "reasoning": {"enabled": False}}, timeout=45)
    except httpx.HTTPError:
        return {"ok": False, "message": "OpenRouter could not be reached. Try again shortly.", "model": model}
    if response.status_code != 200:
        message = {401: "OpenRouter rejected this API key.", 402: "This account has insufficient model credits.",
                   403: "This key is not allowed to use this model.", 404: "OpenRouter could not find this model.",
                   429: "OpenRouter rate limit reached. Try again later."}.get(
                       response.status_code, "The model provider is temporarily unavailable. Try again shortly.")
        return {"ok": False, "message": message, "model": model}
    try:
        choice = response.json()["choices"][0]
        ok = choice.get("finish_reason") == "stop" and bool(choice.get("message", {}).get("content"))
    except (KeyError, IndexError, ValueError, TypeError):
        ok = False
    return {"ok": ok, "message": "Connected. The selected model returned a real response." if ok else
            "The provider returned an incomplete response. Try again shortly.", "model": model}
