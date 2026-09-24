# RETCON implementation

RETCON is an Airflow 3.3 plugin for reviewing the consequences of a story change.

## Package layout

```text
src/retcon/
  plugin.py          Airflow plugin entry point
  bundle.py          Packaged DAG discovery
  cli.py             One-time bundle registration
  dags/retcon.py     Retcon and repair workflows
  web/               Writer interface
  webapp.py          Writer API
  settings.py        OpenRouter Connection settings
  continuity.py      Deterministic checks and impact analysis
  workflow.py        Revision, validation, and publication logic
  store.py           Persistent story state
```

## Writer workflow

1. Open the sample or import a Markdown/text draft.
2. Choose a character and the chapter after which they die.
3. Inspect affected chapters and quoted continuity violations.
4. Generate repairs only for failing paragraphs.
5. Compare changes, then approve or reject the revision.
6. Continue editing or export the manuscript.

## Airflow workflow

`retcon_apply` emits a character-canon Asset event. The event schedules `retcon_cascade`, which checks existing chapters, maps repairs to Common AI tasks, validates results, and waits at a native HITL step. Approval publishes the canon and paragraph changes together.

A rejected model response gets one corrective attempt. Failure or cancellation preserves the published manuscript.

## State and configuration

The OpenRouter model and key live in the `retcon_openrouter` Airflow Connection. Story state lives under `$AIRFLOW_HOME/retcon`; separate API/worker hosts must share that directory through `RETCON_STATE_DIR`.

The package includes its web assets and both DAGs. `retcon configure` registers the native DAG bundle; no files are copied into Airflow's DAG folder.

## Demo scope

The automated canon change is a character's death boundary. Checks cover attributed dialogue after death, backwards linear scene time, and conflicting scene locations. Imported drafts receive a conservative named-character index; scene times and locations are not inferred.

This is a single-writer hackathon demo. See [installation](PLUGIN.md), [demo script](DEMO_SCRIPT.md), and [verification](VERIFICATION.md).
