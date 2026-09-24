# RETCON agent guide

RETCON is a single-writer hackathon demo packaged as an Airflow 3.3 plugin. Writers change a character's fate, inspect continuity failures, review AI-generated paragraph repairs, and approve publication. Keep changes focused on that demo and describe current functionality in the docs.

## Get a tester running

1. Read `README.md` and check whether a demo is already running. Reuse a healthy instance; preserve its story and settings.
2. Choose one startup path from the repository root:
   - **Docker:** `docker compose up --build`
   - **Project venv, macOS/Linux:** `./scripts/local-demo` (requires `uv`). This installs the locked dependencies into `.venv` and runs Airflow there.
3. Open `http://127.0.0.1:8080/plugin/retcon-writer`. Both launchers use Airflow's native no-login demo mode and bind the published service to loopback.
4. If the port is occupied, use `RETCON_PORT=8082 docker compose up --build` or `./scripts/local-demo --port 8082`, then open the matching URL.
5. Confirm the writer loads, the Airflow indicator is available, and both `retcon_apply` and `retcon_cascade` are registered. A startup message alone is not sufficient.
6. In **Settings**, configure OpenRouter model `google/gemma-4-31b-it:free` and the API key, then test and save. A saved key stays in the Airflow Connection; leave its field blank to retain it.

Docker data lives in the named volume declared in `compose.yaml`. Venv data lives in `.retcon/local`. They are separate demo instances. Stop Docker with `Ctrl+C` or `docker compose down`, and the venv launcher with `Ctrl+C`; these preserve data. Keep credentials, runtime state, and `.env` files out of Git and image build contexts.

For installation into an existing Airflow deployment, bundle configuration, or discovery problems, read `docs/PLUGIN.md`. The package uses an `airflow.plugins` entry point plus a native DAG bundle; `retcon configure` registers the bundle. Writers do not create or copy DAG files.

## Walk through the demo

Use a fresh **The Aster Protocol** sample, preserving any user-created draft.

1. Select **Mara → dies at the end of chapter 2**.
2. Choose **Inspect the ripple**. Expect chapters **3, 4, 5** to be affected and dialogue violations in **3 and 4**.
3. Apply the revision. Show the quoted violations and the actual Airflow run link.
4. Review **Changes**, then approve through the writer UI. Publication resumes the native Airflow HITL task.
5. Confirm **3 chapters checked, 2 paragraphs repaired, 3 chapters untouched**. Chapter 5's memory of Mara remains valid.
6. Export Markdown or continue editing.

The model's latency varies. Show real progress and failures; verify publication before reporting success. Keep examples within the implemented death-boundary operation and explicit continuity rules. For a recording, follow `docs/DEMO_SCRIPT.md`.

## Find the implementation

| Area | Files |
| --- | --- |
| Plugin, packaged DAG discovery, configuration CLI | `src/retcon/plugin.py`, `src/retcon/bundle.py`, `src/retcon/cli.py` |
| Asset-triggered workflow, mapped AI repair, HITL | `src/retcon/dags/retcon.py` |
| Continuity rules, revision lifecycle, persistence | `src/retcon/continuity.py`, `src/retcon/workflow.py`, `src/retcon/store.py` |
| Writer API and model Connection settings | `src/retcon/webapp.py`, `src/retcon/settings.py` |
| Vanilla HTML/CSS/JavaScript UI | `src/retcon/web/` |
| Local launchers | `Dockerfile`, `compose.yaml`, `scripts/local-demo` |

Read `docs/BUILD_PLAN.md` for the workflow overview. Model calls use the Common AI provider and `retcon_openrouter` Connection. Story state is a separate JSON store. The published manuscript stays intact until approval; invalid or incomplete repairs cannot publish.

## Verify changes

```sh
uv sync --locked --python 3.12
uv run pytest -q
uv run ruff check src tests
uv build
```

For UI changes, also run `node --check src/retcon/web/app.js` and inspect the page. For launcher, packaging, or DAG changes, smoke-test the affected startup path and confirm plugin discovery, both DAGs, and a working continuity preview. Docker diagnostics: `docker compose ps`, `docker compose logs airflow`, and `docker compose exec airflow airflow dags list-import-errors`.

Use focused tests appropriate to the change. Rebuild the Docker image after source changes. Keep the demo simple: one Airflow runtime, native workflow features, UI-based model setup, and no separate writer service or app-specific account system.

When asked to commit, create a new descriptive commit on top of the current branch. Preserve pushed history; amend or rewrite only when explicitly requested. Push only when requested.
