# RETCON — judge, mentor, and venture assessment

Research checked September 24, 2026. This is a decision brief and proposed positioning; the build plan is a target, not a claim that every feature has shipped.

## Decision: build RETCON, narrow the promise

**Pitch:** “Every data engineer knows backfill. Novelists call it retcon.”

**Writer promise:** Change one story fact, see which later scenes break, and approve only the repairs you want.

Keep the idea. Its strongest moment is a visible chain of cause and effect: the writer changes the past, evidence of contradictions appears, a small repair is proposed, and the writer decides whether it becomes canon. The project becomes generic if the main demonstration is generating five chapters with a chatbot.

**Recommended category: Airflow Can Do That?!** The wildcard fits fiction as an unexpected orchestration workload and requires Airflow to be the engine. Enter Agentic Pipeline only if the submitted execution actually uses the Common AI provider; calling OpenRouter from an ordinary Python task does not satisfy that category's named requirement. The installable Airflow 3.3 package hosts the writer through `AirflowPlugin.fastapi_apps`, embeds it with `external_views`, and ships both workflows through a native DAG bundle. Plugin Powerhouse is therefore an additional technically supported category; choose it if the recording leads with the complete Airflow-hosted application and setup flow. The wildcard recommendation remains appropriate if the story-retcon surprise leads. Submit one category. [Event categories](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/)

## Judge's scorecard

These are subjective design targets, not a probability of winning. Scores assume the demonstrated behaviors work.

| Dimension | Starting idea / 5 | Strong execution / 5 | Evidence that earns the improvement |
| --- | ---: | ---: | --- |
| Creativity and originality | 4 | 4.5 | The retcon/backfill connection is memorable; fact-level impact and constrained repair make it concrete. |
| Airflow feature usage | 2.5 | 4.5 | Actual scheduled tasks, inspectable run IDs, asset events where implemented, bounded repair, durable human gate. |
| Impact and usefulness | 2.5 | 4 | A writer imports or pastes a draft, sees the exact problem, controls the change, and exports readable text. |
| Demo and story | 4 | 5 | An obvious contradiction, preserved passages, an understandable diff, and a clear approval moment. |
| Technical implementation | 2.5 | 4 | Persistent versions, evidence-linked findings, valid failure states, and tests for exceptions and retries. |

The official weights are 25% creativity, 25% Airflow usage, 20% usefulness, 20% demo, and 10% implementation. Spend the last hours on a reliable, readable demo; a second AI agent earns less than a believable result. [Scoring rubric](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/)

## Novelty: defend a specific combination

| Existing product | What its primary documentation already establishes | RETCON's proposed distinction |
| --- | --- | --- |
| Sudowrite | Chapter Continuity links preceding documents and supplies earlier story context to generation. | A canon revision produces an explicit impact report, checkable violations, and reviewable repairs. [Documentation](https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/chapter-continuity/4KL8gFeLZQ6GSBjDWtSbV6) |
| Novelcrafter | Its Codex indexes mentions, tracks time-dependent character progressions, and supplies structured story context. | Reproducible runs and evidence-backed repair transactions, with unchanged material verified and publication gated. [Codex](https://www.novelcrafter.com/features/codex) |
| Plottr | Visual timelines arrange chapters and scenes and can be filtered by characters and places. | A timeline that also runs consistency checks and proposes constrained corrections when canon changes. [Timeline overview](https://docs.plottr.com/article/54-timeline-overview) |

Do not say “the first story bible,” “the first AI continuity editor,” or “never seen before.” These pages establish substantial overlap; they do not constitute an exhaustive competitive audit or prove that competitors lack a similar capability.

A defensible line is: **“RETCON turns a story revision into an observable data workflow: version, find impact, check, repair, review.”** The novelty is how that workflow is made visible and useful, not simply placing an LLM in a DAG.

## What the engineering claim actually means

- **RETCON owns semantic lineage.** Its explicit fact-to-scene index determines which passages may depend on a change.
- **The package owns installation.** One wheel contains the UI, API, and DAGs. A standard plugin entry point loads the application, and one-time native bundle registration makes the workflows discoverable without copying DAG files.
- **Airflow owns orchestration.** It runs declared tasks, handles dependencies and retries, records outcomes, and can schedule consumers after emitted asset events.
- Naming a YAML file as an Asset does not cause Airflow to monitor the file or understand its prose. Code must emit an event after an accepted update, and the application must resolve story-level impact. [Asset scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html)
- “Zero known rule violations” is meaningful. “A perfectly consistent novel” is not established by three rules, structured metadata, or one LLM judge.
- A repair is a proposed new version until the human approves it. A retry cannot silently replace the published manuscript.

The distinction between an ordinary model call and Common AI usage matters. The provider offers Airflow operators for structured generation and model-driven branching; eligibility should be based on the operator actually executed, not an installed package. [Common AI provider](https://airflow.apache.org/docs/apache-airflow-providers-common-ai/stable/index.html)

## Venture view: promising wedge, unvalidated business

**Initial user:** a serial-fiction author, developmental editor, or small narrative-game team revising an existing multi-scene story. Their job is keeping downstream consequences consistent while preserving voice.

**Hypothesis:** users value a trusted change report and a small, reversible patch more than another full-chapter generator. This has not been validated with interviews or paid use.

**Commercial direction:** a continuity-review layer that works with existing writing tools. An editor's review queue, evidence-linked canon, and versioned decisions could become valuable team infrastructure. Airflow is an implementation choice, not the customer-facing selling point or a moat.

**What could become defensible:** an evaluation corpus of real revision errors with permission to use it, an explicit temporal fact model, high-quality user-approved repair history, and integrations that reduce migration effort. None is a moat merely because it is planned.

**Main commercial risks:** writers may reject inferred facts; false alarms destroy trust; existing tools can add adjacent features; a free model may require excessive retries; importing a manuscript poorly can outweigh any downstream benefit.

Do not invent a market size, willingness-to-pay, or revenue forecast. After the hackathon, test a paid per-project continuity review and an editor/team subscription as competing hypotheses.

### Small validation experiment

Recruit five writers or editors with a draft they are permitted to share. Ask each to make one meaningful canon change in a 5–10 scene sample.

1. Observe their current process before showing RETCON.
2. Have them identify affected scenes unaided; then compare against RETCON's report.
3. Measure false positives, missed issues, review time, accepted patches, and unwanted edits.
4. Ask whether they would use the exported changes in their real manuscript.
5. Ask them to choose between two concrete paid offers rather than agreeing that the idea sounds useful.

Proposed continuation gates: at least three people successfully complete the workflow without Airflow help; at least three accept a useful patch; no silently overwritten source text; median review is faster than the user's baseline. These are product decision thresholds, not research findings.

## Alternative ideas, only if the engine cannot carry this demo

| Idea | Hook | Why it is a fallback |
| --- | --- | --- |
| QUESTLINE | Change a game-world fact; find broken quests and NPC dialogue. | Stronger machine-checkable constraints and commercial team workflow, but branching worlds increase scope. |
| CANON DIFF | Review imported writing for contradictions, propose no prose. | Easier to finish and lower model dependence, but a quieter demo. |
| RETCON with guided repair | Same canon cascade; a human edits flagged passages after deterministic checks. | Preserves the core Airflow story if free-model generation is unavailable; label it honestly. |

Do not pivot to a new domain because setup consumed an hour. Cut whole-chapter generation, optional agents, and fancy timeline interaction first.

## Submission and deadline discrepancy

The event landing page lists **September 24** as the submission date. The linked official rules instead list **September 17**, say dates are Pacific Time, and show **“Last Updated: July 23, 2025.”** These pages conflict. Do not assume an extension, an exact closing hour, or an applicable year for the rules' undated timeline. Confirm with the organizer or the registration/submission instructions before relying on acceptance. [Event](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/), [Official rules](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/rules/)

The rules require a new public project on open-source Airflow 3.1+, an OSI-approved license, a public demo of at most three minutes, a written explanation, the category/features, and local run instructions. Use synthetic story material and exclude API credentials from the repository and recording. [Submission requirements](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/rules/)

Final submission wording must describe the verified build. Claim native HITL, Common AI, asset-triggered execution, paragraph-level preservation, or import fidelity only when that exact path was exercised successfully.

