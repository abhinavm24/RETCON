"""Writer workspace mounted and authenticated by the RETCON Airflow plugin."""
from importlib.resources import files
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field

from . import workflow
from .airflow_client import AirflowClient
from .continuity import preview
from . import settings

WEB_ROOT = files("retcon").joinpath("web")

app = FastAPI(title="RETCON — Backfill for stories", version="0.1.0")
app.mount("/static", StaticFiles(directory=WEB_ROOT, check_dir=False), name="static")
airflow = AirflowClient()


class RetconRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=60)
    death_chapter: int = Field(ge=1, le=20)
    instruction: str = Field(default="", max_length=2000)


class Decision(BaseModel):
    approved: bool


class ChapterEdit(BaseModel):
    text: str = Field(min_length=1, max_length=60000)
    title: str | None = Field(default=None, max_length=200)


class ImportRequest(BaseModel):
    title: str = Field(default="Untitled manuscript", max_length=200)
    text: str = Field(min_length=1, max_length=250000)


class ModelSettings(BaseModel):
    provider: Literal["openrouter", "openai"] = "openrouter"
    base_url: str | None = Field(default=None, max_length=2000)
    model: str = Field(default=settings.DEFAULT_MODEL, min_length=3, max_length=160)
    api_key: str | None = Field(default=None, max_length=512, repr=False)


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    # Reject writes from unrelated web origins, no wildcard CORS.
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "DELETE", "PATCH"} and origin:
        from urllib.parse import urlparse
        if urlparse(origin).netloc != request.headers.get("host"):
            return PlainTextResponse("Cross-origin writes are not allowed.", status_code=403)
    return await call_next(request)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request, exc):
    from fastapi.responses import JSONResponse
    # FastAPI normally echoes invalid input; credentials must never be reflected.
    errors = [{key: error[key] for key in ("loc", "msg", "type") if key in error} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/")
def index():
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/styles.css")
def styles():
    return FileResponse(WEB_ROOT / "styles.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(WEB_ROOT / "app.js", media_type="text/javascript")


def engine_available():
    # Availability and permission are evaluated using this user's session.
    return airflow.healthy()


@app.get("/api/state")
def state():
    current = workflow.load_state()
    run = current.get("run")
    if run:
        run["airflow_url"] = airflow.run_url(run)
    current["engine"] = {"available": engine_available(), "model": settings.public_settings()["model"]}
    return current


@app.get("/api/settings")
def get_settings():
    return settings.public_settings()


@app.put("/api/settings")
def update_settings(body: ModelSettings):
    return settings.save_settings(**body.model_dump())


@app.post("/api/settings/test")
def test_model_settings(body: ModelSettings):
    return settings.test_settings(**body.model_dump())


@app.post("/api/retcons/preview")
def preview_retcon(body: RetconRequest):
    return preview(workflow.load_state()["story"], **body.model_dump())


@app.post("/api/retcons", status_code=202)
def create_retcon(body: RetconRequest):
    if not engine_available():
        raise HTTPException(503, "Airflow is unavailable. Check its API server, scheduler, and RETCON DAG bundle, then try again.")
    if not settings.public_settings()["configured"]:
        raise HTTPException(409, "Configure a model in Settings first.")
    run = workflow.start_retcon(**body.model_dump())
    try:
        result = airflow.trigger(run["id"])
        workflow.annotate_run(run["id"], apply_airflow_run_id=result["dag_run_id"])
    except (httpx.HTTPError, KeyError) as exc:
        workflow.fail_run(run["id"], "Airflow could not accept the revision. Check the local scheduler and API.")
        raise HTTPException(503, "Could not trigger the Airflow workflow. See the activity log.") from exc
    return workflow.load_state()["run"]


@app.post("/api/runs/{run_id}/decision")
def decision(run_id: str, body: Decision):
    run = workflow.get_run(workflow.load_state(), run_id)
    if run["status"] != "awaiting_approval":
        raise ValueError("The revision is not waiting for approval.")
    try:
        airflow.decision(run, body.approved)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Airflow could not save your decision. Try again shortly.") from exc
    return {"status": "decision_submitted", "message": "Your decision is saved in Airflow. Publication is processing."}


@app.post("/api/reset")
def reset():
    return workflow.reset_demo()


@app.post("/api/runs/{run_id}/cancel")
def cancel(run_id: str):
    # Invalidate locally first: an old worker cannot stage or publish after this point.
    run = workflow.cancel_run(run_id)
    for dag, native_id in (("retcon_apply", run.get("apply_airflow_run_id")),
                           ("retcon_cascade", run.get("airflow_run_id"))):
        if native_id:
            try:
                airflow.request("PATCH", f"/api/v2/dags/{dag}/dagRuns/{quote(native_id, safe='')}",
                                json={"state": "failed"})
            except httpx.HTTPError:
                # Recovery must work even while the orchestrator is unavailable.
                pass
    return run


@app.put("/api/chapters/{chapter_id}")
def update_chapter(chapter_id: int, body: ChapterEdit):
    return workflow.edit_chapter(chapter_id, **body.model_dump())


@app.post("/api/import")
def import_draft(body: ImportRequest):
    return workflow.import_story(**body.model_dump())


@app.get("/api/export")
def export():
    return PlainTextResponse(workflow.export_markdown(), media_type="text/markdown",
                             headers={"Content-Disposition": 'attachment; filename="retcon-manuscript.md"'})


@app.get("/api/health")
def health():
    return {"status": "ok", "engine_available": engine_available()}
