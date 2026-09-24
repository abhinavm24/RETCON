# RETCON — build plan

This is the prioritized implementation contract and acceptance plan. A planned item is not automatically a shipped feature; the repository's verified runtime and documented limitations determine what may be demonstrated.

## Current completed slice

The build packages the writer UI, API, and both DAGs as the installable `airflow-retcon` plugin for Apache Airflow 3.3, with in-app model/key setup backed by an Airflow Connection, a real two-DAG asset-triggered workflow, Common AI through native OpenRouter, two-attempt paragraph repair, completeness/continuity checks, native HITL approval through the writer UI, cancellation recovery, import/edit/export, and atomic publication. The tested runtime versions, installation checks, and complete approval-path evidence are recorded in [VERIFICATION.md](VERIFICATION.md).

The supplied seed is deliberately compact: **458 words across five chapters** before repair. The automated canon operation is a character's death boundary. Full exception modelling for flashbacks/recordings, editable extracted scene metadata, parsed-import preview, arbitrary twist planning, full manuscript-version browsing, per-patch approval, and collaborative sharing remain roadmap items. Requirements below describe the broader target; they are not claims about those unimplemented features.

## Outcome

A writer opens a five-chapter locked-room mystery aboard research station Aster, changes Mara's fate, and sees which later scenes need attention. RETCON checks first, repairs only demonstrated violations, presents a readable diff, and waits for approval before publishing a new version.

The writer should never need to know what a DAG, XCom, scheduler, task instance, or asset URI is. An optional “View execution” link gives technical judges the underlying Airflow evidence.

## Scope and priorities

| Priority | Capability | Definition of done |
| --- | --- | --- |
| P0 | Writer workspace | Read chapters, select a chapter, inspect story facts, submit a canon revision. |
| P0 | Real orchestration | The primary retcon action creates or triggers a real Airflow run; the UI exposes its run ID and actual progress. |
| P0 | Impact and validation | Store fact dependencies, separate affected from broken, and attach each violation to a scene and a quote. |
| P0 | Small proposed repair | Call the configured OpenRouter model for failing scenes only; validate the response and show a diff. |
| P0 | Approval and history | Keep the current version intact until approval; preserve the old version and record the decision. |
| P0 | Failure UX | Show rate limits, invalid output, exhausted repairs, and unavailable Airflow without presenting success. |
| P1 | Bring your draft | Paste or upload Markdown/plain text with documented chapter boundaries; show the parsed preview before import. |
| P1 | Continue writing | Edit text, save a new draft version, rerun checks, and export Markdown. A reliable manual edit is sufficient for the first iteration. |
| P1 | Share the work | Download a readable manuscript plus an optional JSON review bundle. This is file sharing, not live collaboration. |
| P2 | Deeper AI | Suggest alternative twists, continue a chapter from approved canon, add a semantic reviewer. |
| Later | Product expansion | DOCX fidelity, collaborative accounts, public share links, Google Docs/Scrivener integration, branching realities, richer rules. |

Keep the primary demo narrow enough to fit in three minutes. Do not add chat, agents, embeddings, or a graph database simply to make the architecture look larger.

## Writer journey

1. **Start:** choose the Aster sample or import a draft. State supported file formats and size limits.
2. **Orient:** a chapter list and story-fact panel show where the writer is. Facts display their effective story time and evidence.
3. **Change canon:** submit “Mara dies at the end of chapter 2,” inspect the interpreted effective boundary, and confirm the proposed fact.
4. **Preview impact:** distinguish “unaffected,” “needs checking,” and “contradiction found.” Explain why each scene was selected.
5. **Watch work:** plain-language stages such as “Checking chapter 4” and “Repair attempt 1 of 2.” No simulated percentages.
6. **Review:** show the old and proposed passage, highlighted changes, the triggering fact, and checks that passed or remain unresolved.
7. **Decide:** approve, reject, or edit the proposal. Accepted changes become a new manuscript version.
8. **Continue:** edit another chapter or export the accepted manuscript. A technical execution view remains optional.

For arbitrary imported prose, names alone are not reliable lineage. Mark extracted facts and inferred dependencies as unverified until reviewed; keep the curated sample separate from claims about open-ended import accuracy.

## Technical responsibilities

### Application and persistence

Ship the API, static browser UI, and DAGs in one Python wheel with an `airflow.plugins` entry point. Register the packaged DAGs through Airflow 3.3's native bundle interface using `retcon configure`; preserve existing DAG bundles and avoid generating files at startup. Airflow is the application runtime, and model/key setup belongs in the embedded UI and Airflow Connection.

The current JSON store uses file locks and atomic replacement, with state under `$AIRFLOW_HOME/retcon` or `RETCON_STATE_DIR`. Separate API and worker containers must share this persistent directory. This storage supports the single-writer demo; multi-user operation needs a transactional persistence design.

Persist:

- Manuscript and chapter IDs, scene IDs, prose, structured events, and version hashes.
- Canon facts with stable IDs, a value, an effective story-time boundary, a revision, and source evidence.
- Fact-to-scene dependencies with a reason and provenance: authored, deterministic extraction, or model inference.
- Run ID, input version, canon revision, stage, timestamps, findings, repair attempts, model metadata, errors, and approval state.
- Original and proposed scene text separately, with a record of accepted changes.

Use the same input snapshot throughout a run. If the writer changes the draft before approval, detect the version conflict and require a fresh check instead of applying a stale patch.

### Airflow boundary

The packaged `retcon_cascade` DAG follows this sequence:

```text
load immutable revision
    → compute affected scenes
    → validate existing scenes
    → classify clean / repairable / needs writer
    → repair failing scenes, with a bounded second attempt
    → revalidate proposals
    → wait for decision
    → publish accepted revision
```

The packaged `retcon_apply` ingress DAG validates the canon request and emits a story-bible revision asset. `retcon_cascade` consumes that event and uses its revision metadata to load the intended inputs. The DAG processor discovers both DAGs from `RetconDagBundle` after the one-time bundle configuration.

**Airflow does not infer character dependencies or watch YAML files.** RETCON's lineage index makes the selection; explicit outlet/event code reports the update to Airflow. A shared bible asset may schedule one consumer run, which then selects scenes. That is still meaningful asset-driven orchestration; it is not automatic paragraph dependency inference. [Airflow asset scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html)

A manual DAG trigger is an acceptable first vertical slice. Label it accurately until the asset path has been run. Likewise, an application approval endpoint is not automatically native Airflow HITL. If native HITL is shipped, connect the writer's decision to the actual deferred operator and test resumption.

“Backfill for stories” is the metaphor. Use “Airflow backfill” as an implementation claim only if the Airflow backfill mechanism is actually invoked.

### Deterministic rules and their limits

| Rule | Structured condition | Required exception/context |
| --- | --- | --- |
| Dead character speaks | A living-scene dialogue event occurs after the character's death boundary. | Recorded audio, remembered speech, ghosts, quotations, and flashbacks must be represented explicitly. |
| Impossible simultaneous location | One character has overlapping active intervals in incompatible locations. | Exclude recordings, remote communication, deliberate doubles, and uncertain timestamps. |
| Time moves backwards | Event time regresses within a sequence declared chronological. | Flashbacks and intentionally nonlinear scene sequences are valid when marked. |

Validate the relationship between evidence and prose: a finding's quote must occur in the cited scene, IDs must resolve, and timestamps must parse. A schema-valid event list can still omit a contradiction. Therefore report **known rule results**, not a proof of narrative coherence.

Prioritize the death rule for the live cascade. The location and time rules belong in small fixture tests and can be shown briefly if they work. If they are incomplete, document their limited scope rather than displaying unconditional green badges.

### OpenRouter model integration

Requested model: `google/gemma-4-31b-it:free`. Configure the model and key through the embedded writer's AI settings. Read them server-side from the `retcon_openrouter` Airflow Connection: the password holds the key and `extra.model` holds the model. Never return a saved key to the browser or embed it in frontend code, sample payloads, logs, screenshots, or Git history.

Before building around it, verify that the exact identifier is available to the supplied account and can complete a minimal request. Then verify structured output with a real repair request. Availability, supported parameters, rate limits, and output quality are runtime facts; a `:free` suffix does not guarantee unlimited service.

For the first build, bind the chapter and paragraph ID in the task payload and ask the model for replacement paragraph text only. Recompute the supported dialogue metadata and validate against the current canon. This limits the model's ability to invent IDs or change unrelated passages. Preserve unaffected paragraphs byte-for-byte by applying replacements only to explicitly authorized IDs.

A later structured response can add scene events and a change explanation. If that path is used, reject unknown IDs, absent evidence, oversized output, invalid JSON, and inconsistent metadata rather than treating schema validity as semantic correctness.

Target at most two model repair attempts per scene. A transport retry is a separate, capped policy. A true second repair attempt receives the validation error rather than silently broadening the request. If only task/transport retries exist in the shipped version, say so: a failed recheck must stop for writer attention, and must not be described as an implemented feedback repair loop. After exhaustion, keep the original and request a writer decision.

If Common AI is used, verify the installed provider's API and connection configuration against its matching version, including OpenRouter compatibility. A direct OpenRouter adapter inside a Python task remains an honest wildcard implementation. [Common AI reference](https://airflow.apache.org/docs/apache-airflow-providers-common-ai/stable/index.html)

An LLM judge can suggest possible issues. It should not override an explicit deterministic failure or accept its own unsupported claim as proof. Defer semantic judging until the core check–repair–approval loop is reliable.

## Fixture design that makes the demo honest

Five short chapters, roughly 150–250 words each, are enough to make the reader understand the story while keeping model latency manageable. Full 400–600 word chapters can be added after the cascade works.

| Chapter | Role in demonstration |
| --- | --- |
| 1 | Earlier than the changed fact; a stable control for preservation. |
| 2 | Source of the canon change, with an ending compatible with the confirmed revision or explicitly edited by the writer. |
| 3 | Contains one unmistakable post-death line of active dialogue; requires repair. |
| 4 | Contains a second direct contradiction; requires repair. |
| 5 | References the changed character retrospectively without post-death active dialogue; affected and checked, then preserved. |

Do not count the source edit as an invisible free operation. If chapter 2 is rewritten, include it in the “changed” count, or state “two downstream repairs plus the author's source edit.” The UI should derive all counts from stored versions and findings.

A deceased character's name can appear legitimately. This gives the check-before-rewrite step a useful purpose: selected chapters can pass without generating new prose.

The Aster seed should leave Mara's fate ambiguous after an airlock accident in chapter 2. The writer's canon decision resolves that ambiguity. Do not imply a fully rendered betrayal/death scene was also generated if the action only changes the canon record.

## Eight-hour execution plan

| Time | Work | Exit evidence / cut rule |
| --- | --- | --- |
| 0:00–0:30 | Build and install the wheel in Airflow 3.3; register its DAG bundle; confirm plugin and DAG discovery; probe the exact OpenRouter model. | Capture versions, a real DAG task, and a minimal model response. If the provider path fails, keep wildcard eligibility and simplify the adapter. |
| 0:30–1:15 | Create a stable sample, facts, scene IDs, version storage, and the first retcon DAG. | One change selects the expected candidates and stores a real run ID. |
| 1:15–2:15 | Implement deterministic checks and explainable findings. | Dead speech is caught; a recording/flashback is preserved; unaffected scenes remain unchanged. |
| 2:15–3:15 | Implement narrow repairs, response validation, bounded attempts, and rechecks. | One live model patch clears the intended rule; bad output and service failures end visibly. |
| 3:15–4:15 | Build the writer workspace and progress view. | A user can read, change canon, and inspect a failing quote without Airflow knowledge. |
| 4:15–5:00 | Add diff review, approval/rejection, version-conflict checks, and export. | An unapproved proposal cannot replace the current draft; accepted text exports correctly. |
| 5:00–5:45 | Add paste/Markdown import and manual editing; test chapter splitting. | A short custom draft survives import–edit–export with visible limitations. |
| 5:45–6:30 | Add or verify native asset/HITL integration only if the vertical slice is stable; run focused failure tests. | Evidence shows exactly the orchestration features claimed. At 6:30 freeze functionality. |
| 6:30–7:15 | Rehearse the actual demo, reduce latency, inspect visual readability. | Two clean runs; counts, run IDs, diffs, and approval align. |
| 7:15–8:00 | Record, trim under three minutes, finish README/license/write-up, inspect repository for credentials, prepare submission links. | Public deliverables are usable; deadline discrepancy is resolved with organizer information. |

If Airflow cannot run by hour two, retain the code and product work but do not call it a qualifying working submission. RETCON requires Airflow; do not substitute fabricated task transitions for an execution.

## Focused verification

These are the high-value tests; avoid spending the remaining time testing cosmetic controls.

- Baseline sample has no known violations before the change.
- A canon revision selects the right story-time range and documents selection reasons.
- A name mention without prohibited behavior does not trigger a repair.
- A legitimate flashback/recording does not become a false death violation.
- Wrong IDs, invalid JSON, quote mismatches, and invalid temporal values are rejected.
- Recheck failures lead to the bounded second attempt, then human escalation.
- Model/network failure cannot publish success or drop the original text.
- Repeated runs and approval requests do not duplicate a publication.
- A stale proposal cannot overwrite a newer draft.
- Unaffected scene hashes are identical; changed counts equal actual changes.
- Approval/rejection resumes the real orchestration state if native HITL is claimed.
- Export contains the accepted manuscript, not the unapproved proposal.

## Completion evidence and scope labels

At handoff, record installed versions, test results, the actual DAG run ID, exact model used, live-call outcome, and a screenshot or run log for the complete approval path. Separate:

- **Implemented:** code exists.
- **Verified locally:** the relevant execution succeeded.
- **Unavailable here:** code could not run because a dependency or external service was unavailable.
- **Roadmap:** not implemented.

That distinction should appear in the README and final submission, especially for real Airflow, Common AI, native HITL, asset triggers, and generic-manuscript extraction.
