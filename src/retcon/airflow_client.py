"""Small server-side adapter for Airflow's supported REST API v2 and native HITL."""
from urllib.parse import quote

import httpx
from .plugin_auth import airflow_token


class AirflowClient:
    def __init__(self, base_url=None):
        self._base_url = base_url

    @property
    def url(self):
        if self._base_url is not None:
            return self._base_url.rstrip("/")
        from airflow.configuration import conf
        return (conf.get("api", "base_url", fallback=None) or
                f"http://127.0.0.1:{conf.getint('api', 'port', fallback=8080)}").rstrip("/")

    def request(self, method, path, **kwargs):
        token = airflow_token.get()
        if not token:
            raise ValueError("Sign in to Airflow before using RETCON.")
        response = httpx.request(method, self.url + path, headers={"Authorization": "Bearer " + token},
                                 timeout=15, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def healthy(self):
        try:
            data = self.request("GET", "/api/v2/dags/retcon_cascade")
            return not data.get("is_paused", True)
        except (httpx.HTTPError, KeyError):
            return False

    def trigger(self, revision_id):
        for dag in ("retcon_apply", "retcon_cascade"):
            self.request("PATCH", f"/api/v2/dags/{dag}", json={"is_paused": False})
        return self.request("POST", "/api/v2/dags/retcon_apply/dagRuns", json={
            "dag_run_id": "retcon__" + revision_id, "logical_date": None, "conf": {"run_id": revision_id}})

    def decision(self, run, approved):
        dag = run.get("airflow_dag_id", "retcon_cascade")
        dag_run = run.get("airflow_run_id")
        if not dag_run:
            raise ValueError("Airflow is preparing the editor's decision. Try again in a moment.")
        path = f"/api/v2/dags/{dag}/dagRuns/{quote(dag_run, safe='')}"
        details = self.request("GET", path + "/hitlDetails", params={"response_received": "false"})
        if not details.get("hitl_details"):
            raise ValueError("Airflow has not opened the approval step yet. Try again in a moment.")
        return self.request("PATCH", path + "/taskInstances/editor_approval/-1/hitlDetails",
                            json={"chosen_options": ["Publish" if approved else "Reject"], "params_input": {}})

    def status(self, dag_id, run_id):
        return self.request("GET", f"/api/v2/dags/{dag_id}/dagRuns/{quote(run_id, safe='')}")

    def run_url(self, run):
        dag = run.get("airflow_dag_id", "retcon_apply")
        run_id = run.get("airflow_run_id", "retcon__" + run["id"])
        return f"/dags/{dag}/runs/{quote(run_id, safe='')}"
