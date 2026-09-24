# Airflow 3.3 package verification — September 24, 2026

RETCON is now an installable `airflow-retcon` wheel targeting Apache Airflow 3.3.x. The earlier custom project setup is no longer required.

## Installed-package checks

- Built wheel and source distribution with `uv build`.
- Installed the wheel into a separate Python 3.12 environment with **Apache Airflow 3.3.2**, outside the repository and without `PYTHONPATH` pointing at source.
- Airflow discovered `RetconPlugin` through the standard `airflow.plugins` entry point.
- `retcon configure` registered `retcon.bundle.RetconDagBundle` and preserved the default local bundle. A second run was byte-for-byte idempotent.
- On a fresh Airflow home, the command let Airflow initialize its full config first; Fernet and JWT signing keys were present afterward. Secret values were not printed.
- The native DAG processor discovered **retcon_apply** and **retcon_cascade** from the installed wheel, with zero import errors.
- API server, scheduler, DAG processor, triggerer, and metadata database were healthy.
- Plugin HTML, JavaScript, state, and settings endpoints responded successfully.

Final simplified demo suite: **131 tests passed** against the installed wheel, without warnings or skipped tests. The earlier 138-test result included role checks that were intentionally removed for the single-user hackathon demo. The no-login browser path was verified with the published story visible.

## Full Airflow 3.3 run

Revision **612a8c98e0094548** ran from the installed package after the saved OpenRouter Connection was transferred to the new metadata database.

- Consumer: `asset_triggered__2026-09-24T16:01:56.886329+00:00_GSgkYaep`.
- Worker logs identify `site-packages/retcon/dags/retcon.py` as the executed source.
- Both real Common AI calls used `google/gemma-4-31b-it:free` through the stored Connection.
- Both repaired paragraphs passed validation. **3 chapters checked, 2 repaired, 3 untouched.**
- Native HITL approval resumed the DAG and published at `2026-09-24T16:17:08.386374+00:00`.
- A long wall-clock pause during generation was traced to macOS idle sleep, followed by a transient provider retry. It was not evidence of a failed package migration; avoid counting that paused interval as model latency.

## Demo scope

The local demo uses Airflow's built-in `simple_auth_manager_all_admins` mode and binds to loopback, so there is no login prompt. RETCON adds no separate account or role system. Its small session adapter forwards Airflow's native session to workflow API calls. Model keys remain server-side in an encrypted Airflow Connection.

This is a single-writer demo. In a distributed Airflow deployment, its components need a shared persistent state directory. No public package publication, repository push, or contest submission has been performed.

<details>
<summary>Earlier Airflow 3.1 prototype verification</summary>

# Local verification — September 24, 2026

## Environment exercised

- Astro CLI 1.45.0 and Docker 29.7.2 on macOS.
- Astro Runtime 3.1-21; actual Airflow version `3.1.8+astro.8`, Python 3.12.
- Common AI provider 0.9.0 and Standard provider 1.18.0.
- Required model: `google/gemma-4-31b-it:free`, through OpenRouter.
- Initial standalone writer: `http://127.0.0.1:8000` (now stopped). Current embedded writer: `http://localhost:8080/plugin/retcon-writer`; mounted app: `/retcon/`.

The live execution used the existing local runtime image with the pinned dependency versions. A subsequent plain `astro dev parse` successfully rebuilt the repository Dockerfile and requirements and passed both DAG integrity tests. The new image was inspected: dependency versions match the exercised runtime, and neither private environment file nor mutable story state is included. This validates a source image rebuild on this Mac; a separate clean-machine installation has not been exercised.

## Automated verification

- **114 pytest cases passed inside the actual Airflow container** after the plugin conversion (100 also pass in the smaller local environment; Airflow-specific modules are tested in the container). Coverage includes plugin authentication/authorization, settings persistence and secret handling, empty dynamic maps, and deterministic checks, preservation of untouched paragraphs, atomic publishing, stale/cancelled runs, invalid and incomplete generations, import/edit/export, native HITL adapter requests, backend errors, and origin checks.
- A fresh Astro source image build passed; both real DAG parse/integrity tests passed (2 tests, 1.54 seconds).
- Ruff and `node --check web/app.js` passed.
- Git/Docker ignores exclude private credentials and runtime state. A scan found no OpenRouter credential pattern in tracked files.

Two development dependency deprecation warnings are emitted by Starlette/httpx and AnyIO during TestClient tests; there are no test failures.

## Real integration evidence

The application triggered `retcon_apply`, its successful producer emitted a character-canon Asset event, and the Airflow scheduler automatically created `retcon_cascade` runs. This is real event scheduling, not an animated graph or a direct invocation disguised as an asset trigger.

Native Common AI tasks called the required free model, generated real paragraph replacements, and persisted only candidates that passed the application checks. Earlier attempts also exercised rejection and infrastructure-failure paths:

- An initial candidate retained a historical mention of Mara. The stricter replacement contract rejected it; both repair attempts remained unpublished. The prompt now states that replacement paragraphs must omit the dead character's name. This restriction applies to replacement generation, not to all manuscript references: the seeded memory chapter is preserved.
- A later provider result ended with an open quotation and dropped a clue. Completeness checks now run at staging, review, and publication and reject unbalanced quotes, missing terminal punctuation, and unusually short replacements.
- OpenRouter's upstream provider intermittently returned 500/502 responses. Airflow/SDK retries and the writer's failure state exposed these failures while keeping the manuscript intact.
- The generic OpenAI adapter path was replaced by Pydantic AI's native `openrouter:` model integration. Its model profile uses OpenRouter-compatible `max_tokens`; the native-provider live run is recorded below. The profile difference is verified; it does not establish that every upstream error was caused by the previous adapter.

## Completed approval-to-publication run

- Application revision: `e7758966ac3d43c1`.
- Producer: `retcon_apply / retcon__e7758966ac3d43c1`.
- Asset-scheduled consumer: `retcon_cascade / asset_triggered__2026-09-24T14:44:33.896698+00:00_2xK8gzZM`.
- Candidate validation completed at **14:46:47 UTC**, about **2 minutes 14 seconds** after the consumer began. One paragraph needed the second content-repair pass. Provider retries also contributed to the elapsed time.
- **Approve revision was clicked in the writer browser UI.** Airflow's native HITL record has `response_received=true`, `chosen_options=["Publish"]`, and response time `2026-09-24T14:48:00.991284Z`.
- Airflow resumed and published at `2026-09-24T14:48:07.743580+00:00`; the native DAG run finished **success**.
- Published canon: Mara is dead after chapter 2; manuscript version advanced to 2.
- Actual metrics: **3 chapters checked, 2 chapters/2 paragraphs rewritten, 3 chapters untouched**.
- A direct comparison against the seed confirmed **chapters 1, 2, and 5 are identical**, and **13 of 15 paragraph texts are byte-for-byte unchanged**.
- Rechecking the published story returned **zero violations of the implemented rules**.

Chapter 3 now gives the clue to Ivo without making him claim he hid the logs. Chapter 4 changes only the speaker's name from Mara to Ivo. The memory of Mara in chapter 5 stays intact.

This was real model output and real native approval. It is not evidence of exhaustive narrative correctness or guaranteed free-endpoint availability. Use a labelled elapsed-time cut when recording the three-minute submission.

## Browser checks

The writer workspace was opened in the Codex browser and visually inspected. Real manuscript navigation, continuity evidence, impact chips, model-generated paragraph comparisons, engine status, failure activity, browser approval, and the final published version rendered from backend state. Controls for import/edit/export and revision decisions are wired to the tested API. No browser full-matrix or accessibility certification is claimed.

## Airflow-hosted plugin verification

- `AirflowPlugin.fastapi_apps` serves `/retcon/`; `external_views` embeds it at `/plugin/retcon-writer`, reachable through **Browse → RETCON writer**.
- Browser **Test connection** returned a real Gemma response; **Save settings** persisted the selected model while retaining the existing key. One earlier model test failed, followed by a successful retry; free-provider variability remains visible.
- The existing key was migrated server-side into `retcon_openrouter`; encrypted password storage was verified. The worker environment no longer defines `AIRFLOW_CONN_RETCON_OPENROUTER`.
- Anonymous settings requests returned 401. Container tests cover cookie/bearer authentication, request-scoped token forwarding, DAG permissions, Connection permissions, and same-origin browser mutations.
- The old port-8000 process was stopped; 8080 remains the serving port.

The full demo was repeated from the seed using only the embedded UI and the configured metadata-database Connection:

- Revision `2829e7d7cb414ea6`.
- Consumer `asset_triggered__2026-09-24T15:16:31.057625+00:00_InTC3Hjp`.
- Both Common AI calls and validations passed on their first content attempts. No repair retry was needed; the empty retry map skipped correctly.
- Ready for review at `15:18:07 UTC`, about **1 minute 36 seconds** after the consumer started.
- Browser approval recorded as native HITL `chosen_options=["Publish"]` at `15:19:05.241513Z`.
- Published at `15:19:07.313700+00:00`; native DAG state **success**.
- **3 checked / 2 rewritten / 3 untouched**; chapters **1, 2, and 5 identical**; zero violations of the implemented rules.

During verification, a no-op revision exposed Airflow returning `None` for a zero-length mapped result. Both downstream consumers now handle that value. Four focused tests exercise no-repair and no-retry cases; the successful full run also exercised the empty retry path. Prior synthetic rehearsal history was retained in ignored `.retcon/pre-plugin-rehearsal.json` before restoring the sample.

## Boundaries

- Unit/API tests use isolated state and mocked Airflow requests. Real orchestration evidence is recorded separately above.
- Approval is a native Airflow HITL response; a model cannot publish directly.
- Import is a conservative prototype: Markdown/plain numbered chapter headings, explicit attributed character names, and no inferred time/location metadata.
- No public repository, video upload, or contest submission was performed.

</details>
