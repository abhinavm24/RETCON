# RETCON as an Airflow 3.3 plugin

`airflow-retcon` is a Python package for **Apache Airflow 3.3.x**. Its wheel contains the plugin, application code, static writer UI, and two DAGs. Airflow's standard `airflow.plugins` entry point loads `retcon.plugin:RetconPlugin`; there is no project-specific plugin loader or separate writer service.

The plugin registers a FastAPI sub-application at `/retcon` and an `external_views` navigation item that embeds it inside the Airflow shell.

```text
Airflow login
  → Browse → RETCON writer
    → AI settings: model + API key → test → save
    → import/read/edit manuscript
    → inspect canon revision → actual asset-triggered DAG
    → review exact patches → native HITL decision → publish
```

## Install and discover the DAGs

Build the wheel from the repository with `uv build`. In the existing Airflow environment:

```sh
pip install /path/to/airflow_retcon-0.1.0-py3-none-any.whl
retcon configure
```

`retcon configure` adds a native DAG bundle named `retcon` with class `retcon.bundle.RetconDagBundle` to Airflow's `[dag_processor] dag_bundle_config_list`. It preserves existing bundles, including Airflow's default local DAG bundle. Running it again does not add a duplicate entry. To choose a configuration file explicitly:

```sh
retcon configure --airflow-config /path/to/airflow.cfg
```

For deployments that manage Airflow configuration externally, inspect the merged value instead:

```sh
retcon configure --print
```

Apply that JSON as the deployment's `AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST` value. An environment override takes precedence over `airflow.cfg`; the command will not silently edit an ineffective file when that override is present. Indirect `_CMD` and `_SECRET` configuration sources need to be updated through the deployment's own configuration management.

Install the same package and apply the same bundle configuration on the API server, scheduler, DAG processor, triggerer, and workers as applicable, then restart those components. The DAG processor discovers `retcon_apply` and `retcon_cascade` from the installed bundle. Confirm the plugin appears in `airflow plugins`, both DAGs appear in `airflow dags list`, and `airflow dags list-import-errors` reports no RETCON errors.

**Installing a plugin does not itself register DAGs in Airflow.** The one-time bundle registration supplies that native discovery path. The package does not generate or copy DAG files on startup, and no files need to be placed in an Airflow `plugins/` or `dags/` directory. After registration, normal Airflow DAG discovery handles both workflows. Like the local-folder bundle, this bundle uses the currently installed code and does not retain historical package versions; upgrade all components together between active revisions.

The repository is a package, not an Astro template. It can be installed in any supported Airflow 3.3 deployment, including an existing Astro deployment. No `.env` file or runtime selector is required.

## Package layout

```text
pyproject.toml           package dependencies and Airflow/CLI entry points
src/retcon/plugin.py     AirflowPlugin registration
src/retcon/bundle.py     native DAG bundle
src/retcon/cli.py        one-time bundle configuration
src/retcon/dags/         retcon_apply and retcon_cascade definitions
src/retcon/webapp.py     writer HTTP API
src/retcon/web/          packaged HTML, CSS, and JavaScript
src/retcon/              continuity, persistence, model setup, and workflow code
tests/                  focused implementation and installation checks
```

## Where configuration belongs

| Value | Storage | Reason |
| --- | --- | --- |
| OpenRouter API key | Password field of `retcon_openrouter` Airflow Connection | Common AI consumes a Connection; Airflow encrypts its password using the configured Fernet key. |
| Selected model | `extra.model`, such as `openrouter:google/gemma-4-31b-it:free` | Common AI resolves the model from the same Connection. |
| DAG discovery | Airflow's `dag_bundle_config_list` | The DAG processor loads the installed package using its native bundle interface. |
| Manuscript/revision state | `$AIRFLOW_HOME/retcon`, or `RETCON_STATE_DIR` | Persistent single-workspace storage with file locking and atomic publication; contains no provider credential. |

The settings API returns the model, configured/key-present flags, and editability. It never returns the key or a key suffix. The Test button makes a small real model request from the server. Failures are sanitized, and request validation does not echo submitted credentials. Saving a blank key retains the stored credential.

Connection settings are locked during an active revision. Changing the model through the writer UI requires no Airflow restart. Remove any `AIRFLOW_CONN_RETCON_OPENROUTER` environment override because environment-based connections outrank the metadata database and would hide changes saved in the UI.

## Deployment and state

The API and executing tasks must see the same persistent state directory. On one machine, the default `$AIRFLOW_HOME/retcon` is sufficient when all components use the same Airflow home. In a distributed or container deployment, mount shared storage and set the same `RETCON_STATE_DIR` for the API server and task workers. The filesystem must support file locks and atomic replacement.

RETCON supports one writer and one active revision at a time.

## Demo access

This is a single-user hackathon demo. Start native Airflow with `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True` and `AIRFLOW__API__HOST=127.0.0.1` to skip its login screen while keeping the demo local. RETCON forwards Airflow's native session to workflow API calls; it has no separate account or role system. The model/key setup remains in the writer UI, backed by an encrypted Airflow Connection.

## Pitch and evidence

**“Airflow is the writing room: install one package, configure a model, change the past, and review the consequences without leaving the app.”**

For Plugin Powerhouse, demonstrate Airflow's plugin listing and the embedded RETCON navigation first. For the wildcard category, lead with the character-death cascade and reveal that the entire workspace lives in Airflow. Only one category should be submitted.

The exact tested versions, installation checks, and completed workflow evidence are maintained in [VERIFICATION.md](VERIFICATION.md).

Sources: [Airflow 3.3.2 plugins](https://airflow.apache.org/docs/apache-airflow/3.3.2/administration-and-deployment/plugins.html), [Airflow 3.3.2 DAG bundles](https://airflow.apache.org/docs/apache-airflow/3.3.2/administration-and-deployment/dag-bundles.html), [Common AI connections](https://airflow.apache.org/docs/apache-airflow-providers-common-ai/stable/connections/pydantic_ai.html), [Connection lookup precedence](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html).
