# RETCON — Backfill for stories

**Category:** Airflow Can Do That?!

**One-line pitch:** Every data engineer knows backfill. Novelists call it retcon.

RETCON is a writer's continuity workbench packaged as an installable Apache Airflow 3.3 plugin. One Python wheel supplies the embedded application and both workflow DAGs; a native DAG bundle makes the workflows discoverable after one-time configuration. Its embedded UI includes model/key setup backed by an encrypted Airflow Connection. An author changes one character's fate, sees the affected chapters and exact contradictions, and approves small AI-generated repairs. The writer works with manuscripts, story facts, and before/after passages; Airflow operates behind the scenes.

The demo starts with a five-chapter mystery aboard Aster, a remote research station. Resolving Mara's fate as dead after chapter 2 affects three later chapters. Two give her live dialogue and need repair; the third remembers her, so it stays unchanged. The author sees why the passages failed, reviews the proposed corrections, and decides whether to publish.

## How it works

A writer request triggers `retcon_apply`, which emits an explicit character-canon Asset event. That event schedules `retcon_cascade`. RETCON's dependency index identifies affected passages; deterministic checks return evidence. The DAG dynamically maps only failed paragraphs to the Common AI provider's `@task.llm`, using OpenRouter and `google/gemma-4-31b-it:free`. Invalid suggestions get one corrective attempt. Native `HITLOperator` approval is exposed through the writer workspace using Airflow REST API v2. Approval atomically publishes a new manuscript/canon version; rejection preserves the original.

## What was hard

The key design challenge was separating application knowledge from orchestration: Airflow understands declared dependencies, not fiction. RETCON therefore maintains explicit story references and emits real asset events. Another challenge was making the human gate useful without forcing writers into Airflow's UI. Finally, generated prose cannot be trusted just because its metadata claims to be valid, so replacements are checked before staging and again before publication.

## Airflow features

Apache Airflow 3.3, a standard `airflow.plugins` package entry point, `AirflowPlugin` with `fastapi_apps` and embedded `external_views`, a native packaged DAG bundle, connection-backed model setup, asset-triggered scheduling and event metadata, TaskFlow, dynamic task mapping, Common AI `@task.llm`, bounded corrective repair, retries, native HITL, and an approved-manuscript output Asset.

## Honest limits

This is a single-writer prototype using shared persistent filesystem state; API and worker components must access the same state directory. The automated canon edit is a character's death after a chosen chapter. The checks are narrow, and arbitrary manuscript semantics remain an editorial judgement. The backfill connection is a product analogy; the demo uses asset-triggered revision runs, not Airflow's historical-interval backfill endpoint.

## Submission fields to fill

- Public repository URL: pending publication.
- Public demo URL, no longer than three minutes: pending recording/upload.
- Local run instructions: repository README.

The project is MIT licensed and uses original synthetic fiction. No credentials belong in the repository, recording, or written submission.
