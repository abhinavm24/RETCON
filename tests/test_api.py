"""Exercise the writer-facing HTTP contract without Airflow or model network calls."""

from unittest.mock import Mock, create_autospec

import httpx
import pytest
from fastapi.testclient import TestClient

from retcon import webapp as workspace
from retcon import settings, store, workflow
from retcon.airflow_client import AirflowClient
from retcon.plugin_auth import airflow_token
from retcon.seed import seed_story


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(settings, "public_settings", lambda: {
        "configured": True, "model": settings.DEFAULT_MODEL,
    })
    backend = create_autospec(AirflowClient, instance=True)
    backend.healthy.return_value = True
    backend.trigger.side_effect = lambda run_id: {"dag_run_id": "retcon__" + run_id}
    backend.run_url.return_value = "/dags/retcon_cascade/runs/test"
    monkeypatch.setattr(workspace, "airflow", backend)
    with TestClient(workspace.app) as test_client:
        yield test_client, backend


def retcon_body():
    return {"character_id": "mara", "death_chapter": 2, "instruction": "Mara dies at the airlock."}


def reviewable_run():
    run = workflow.start_retcon(**retcon_body())
    for payload in workflow.check_run(run["id"]):
        workflow.save_candidate(
            run["id"], payload["chapter_id"], payload["paragraph_id"], payload["before"].replace("Mara", "Ivo")
        )
    workflow.finish_candidates(run["id"])
    workflow.annotate_run(run["id"], airflow_dag_id="retcon_cascade", airflow_run_id="asset_triggered__example")
    return run["id"]


def test_preview_explains_three_dependent_chapters_and_two_repairs_without_mutation(client):
    browser, backend = client
    before = store.load_state()
    response = browser.post("/api/retcons/preview", json=retcon_body())
    assert response.status_code == 200
    impact = response.json()
    assert impact["affected"] == [3, 4, 5]
    assert {issue["chapter_id"] for issue in impact["issues"]} == {3, 4}
    assert impact["metrics"] == {"checked": 3, "rewritten": 2, "untouched": 3}
    assert store.load_state() == before
    backend.trigger.assert_not_called()


def test_unavailable_airflow_returns_service_error_without_creating_a_revision(client):
    browser, backend = client
    backend.healthy.return_value = False
    before = store.load_state()
    response = browser.post("/api/retcons", json=retcon_body())
    assert response.status_code == 503
    assert store.load_state() == before
    backend.trigger.assert_not_called()


def test_scheduler_trigger_failure_is_visible_and_keeps_the_original_manuscript(client):
    browser, backend = client
    backend.trigger.side_effect = httpx.ConnectError("Scheduler cannot be reached")
    original = store.load_state()["story"]
    response = browser.post("/api/retcons", json=retcon_body())
    assert response.status_code == 503
    current = store.load_state()
    assert current["story"] == original
    assert current["run"]["status"] == "failed"
    assert any(event["kind"] == "error" for event in current["run"]["events"])
    backend.trigger.assert_called_once_with(current["run"]["id"])


def test_start_revision_returns_accepted_and_records_the_real_orchestrator_run(client):
    browser, backend = client
    response = browser.post("/api/retcons", json=retcon_body())
    assert response.status_code == 202
    run = response.json()
    backend.trigger.assert_called_once_with(run["id"])
    assert run["status"] == "queued"
    assert run["apply_airflow_run_id"] == "retcon__" + run["id"]
    assert store.load_state()["story"] == seed_story()
    state_response = browser.get("/api/state")
    assert state_response.status_code == 200
    assert state_response.json()["run"]["airflow_url"].startswith("/dags/")
    assert state_response.json()["engine"] == {"available": True, "model": settings.DEFAULT_MODEL}


@pytest.mark.parametrize("approved", [True, False])
def test_editor_decision_goes_through_native_airflow_and_waits_for_publication(client, approved):
    browser, backend = client
    run_id = reviewable_run()
    before = store.load_state()
    response = browser.post(f"/api/runs/{run_id}/decision", json={"approved": approved})
    assert response.status_code == 200
    assert response.json()["status"] == "decision_submitted"
    backend.decision.assert_called_once_with(before["run"], approved)
    assert store.load_state() == before, "Only the orchestrated publication step may publish the candidate."


def test_decision_failure_preserves_the_review_and_reports_that_retry_is_needed(client):
    browser, backend = client
    run_id = reviewable_run()
    before = store.load_state()
    backend.decision.side_effect = httpx.ConnectError("Airflow is offline")
    response = browser.post(f"/api/runs/{run_id}/decision", json={"approved": True})
    assert response.status_code == 503
    assert store.load_state() == before


def test_editor_cannot_submit_before_airflow_opens_approval(client):
    browser, backend = client
    run = workflow.start_retcon(**retcon_body())
    response = browser.post(f'/api/runs/{run["id"]}/decision', json={"approved": True})
    assert response.status_code == 409
    backend.decision.assert_not_called()
    assert store.load_state()["story"] == seed_story()


def test_decision_for_an_old_revision_cannot_touch_the_current_review(client):
    browser, backend = client
    reviewable_run()
    before = store.load_state()
    response = browser.post("/api/runs/stale-revision/decision", json={"approved": True})
    assert response.status_code == 409
    backend.decision.assert_not_called()
    assert store.load_state() == before


@pytest.mark.parametrize("approved, option", [(True, "Publish"), (False, "Reject")])
def test_airflow_adapter_submits_native_hitl_options_without_publishing_locally(monkeypatch, approved, option):
    backend = AirflowClient()
    request = create_autospec(backend.request)
    request.side_effect = [{"hitl_details": [{"task_id": "editor_approval"}]}, {"response_received": True}]
    monkeypatch.setattr(backend, "request", request)
    run = {"airflow_dag_id": "retcon_cascade", "airflow_run_id": "asset run/with punctuation"}
    assert backend.decision(run, approved) == {"response_received": True}
    calls = request.call_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == "GET"
    assert calls[1].args[0] == "PATCH"
    assert calls[1].kwargs["json"] == {"chosen_options": [option], "params_input": {}}
    assert "asset%20run%2Fwith%20punctuation" in calls[1].args[1]


def test_airflow_adapter_requires_a_user_session_without_attempting_service_login(monkeypatch):
    backend = AirflowClient()
    request = Mock()
    login = Mock()
    monkeypatch.setattr(httpx, "request", request)
    monkeypatch.setattr(httpx, "post", login)
    marker = airflow_token.set(None)
    try:
        with pytest.raises(ValueError, match="Sign in to Airflow"):
            backend.request("GET", "/api/v2/dags/retcon_cascade")
    finally:
        airflow_token.reset(marker)
    request.assert_not_called()
    login.assert_not_called()


def test_airflow_adapter_forwards_each_request_session_without_retaining_credentials(monkeypatch):
    backend = AirflowClient(base_url="http://airflow.example")
    response = httpx.Response(200, json={"is_paused": False}, request=httpx.Request("GET", backend.url))
    request = Mock(return_value=response)
    login = Mock()
    monkeypatch.setattr(httpx, "request", request)
    monkeypatch.setattr(httpx, "post", login)

    for user_token in ("first-writer-session", "second-writer-session"):
        marker = airflow_token.set(user_token)
        try:
            assert backend.request("GET", "/api/v2/dags/retcon_cascade") == {"is_paused": False}
        finally:
            airflow_token.reset(marker)

    assert [call.kwargs["headers"]["Authorization"] for call in request.call_args_list] == [
        "Bearer first-writer-session", "Bearer second-writer-session",
    ]
    marker = airflow_token.set(None)
    try:
        with pytest.raises(ValueError, match="Sign in to Airflow"):
            backend.request("GET", "/api/v2/dags/retcon_cascade")
    finally:
        airflow_token.reset(marker)
    assert request.call_count == 2
    login.assert_not_called()


def test_import_edit_and_export_support_a_writer_round_trip(client):
    browser, backend = client
    imported = browser.post("/api/import", json={
        "title": "The Last Door",
        "text": '# Arrival\n\nNora said, “Come inside.”\n\n## Departure\n\nNora whispered, “Stay.”',
    })
    assert imported.status_code == 200
    assert imported.json()["story"]["title"] == "The Last Door"
    assert len(imported.json()["story"]["chapters"]) == 2
    replacement = 'Nora whispered, “Stay a little longer.”\n\nThe door remained open.'
    edited = browser.put("/api/chapters/2", json={"text": replacement, "title": "An invitation"})
    assert edited.status_code == 200
    assert edited.json()["story"]["version"] == 2
    exported = browser.get("/api/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "attachment" in exported.headers["content-disposition"]
    assert "# The Last Door" in exported.text
    assert "## 2. An invitation" in exported.text
    assert replacement in exported.text
    backend.trigger.assert_not_called()


@pytest.mark.parametrize("origin", ["https://unrelated.example", "http://testserver:9999", "null"])
def test_cross_origin_manuscript_writes_are_blocked_before_mutation(client, origin):
    browser, backend = client
    before = store.load_state()
    response = browser.put("/api/chapters/1", headers={"Origin": origin}, json={"text": "Sera said hello."})
    assert response.status_code == 403
    assert store.load_state() == before
    backend.trigger.assert_not_called()


def test_same_origin_writer_request_is_accepted(client):
    browser, _ = client
    response = browser.put("/api/chapters/1", headers={"Origin": "http://testserver"}, json={"text": "Sera said hello."})
    assert response.status_code == 200
    assert response.json()["story"]["chapters"][0]["paragraphs"][0]["text"] == "Sera said hello."


@pytest.mark.parametrize("text, status", [("", 422), (" \n ", 409)])
@pytest.mark.parametrize("method, path", [("post", "/api/import"), ("put", "/api/chapters/1")])
def test_empty_manuscript_input_returns_a_user_error_and_preserves_current_work(client, text, status, method, path):
    browser, _ = client
    before = store.load_state()
    response = getattr(browser, method)(path, json={"text": text})
    assert response.status_code == status
    assert store.load_state() == before


def test_health_status_reports_backend_availability(client):
    browser, backend = client
    backend.healthy.return_value = False
    response = browser.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "engine_available": False}


def test_reset_returns_the_original_demo_after_a_writer_edit(client):
    browser, _ = client
    browser.put("/api/chapters/1", json={"text": "Sera said hello."})
    response = browser.post("/api/reset")
    assert response.status_code == 200
    assert response.json()["story"] == seed_story()
    assert response.json()["run"] is None


def test_cancel_unblocks_a_writer_even_if_airflow_cannot_be_reached(client):
    browser, backend = client
    started = browser.post("/api/retcons", json=retcon_body())
    assert started.status_code == 202
    run_id = started.json()["id"]
    workflow.annotate_run(run_id, airflow_run_id="asset_triggered__example")
    backend.request.side_effect = httpx.ConnectError("Airflow stopped after accepting the revision")
    original = store.load_state()["story"]

    response = browser.post(f"/api/runs/{run_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert store.load_state()["story"] == original
    assert store.load_state()["run"]["status"] == "cancelled"
    assert backend.request.call_count == 2
    backend.decision.assert_not_called()
    edited = browser.put("/api/chapters/1", json={"text": "Sera said the work could continue."})
    assert edited.status_code == 200
    assert edited.json()["run"] is None
