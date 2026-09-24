# RETCON — demo script and recording plan

**Target duration: 2 minutes 45 seconds.** Leave fifteen seconds of margin under the contest's three-minute maximum. This is a planned script: match every sentence to the actual verified build before recording. [Official submission requirements](https://www.astronomer.io/events/beyond-the-dag-data-engineering-hackathon-2026/rules/)

## The story the viewer must understand

A writer changes an established fact. That fact has consequences elsewhere. RETCON identifies the affected scenes, proves the concrete contradictions it knows how to check, proposes small repairs, and lets the writer accept them. Airflow runs the process; the writer uses a writing interface.

The central surprise is **changing the past without rewriting the whole story**. The second surprise is that an affected chapter can pass the new checks and remain untouched.

## Preflight

- Install the `airflow-retcon` wheel in Airflow 3.3, run `retcon configure`, and restart the relevant Airflow components. Confirm the plugin is loaded, the scheduler is healthy, and both packaged DAGs are present.
- Verify the exact configured OpenRouter model with the supplied account. Run one actual constrained repair before recording.
- Open the writer workspace and its linked Airflow run view in separate tabs.
- Reset to the named sample revision using the documented sample reset path. Do not quietly reuse a previously approved repair as the baseline.
- Confirm the sample's checks pass before changing canon.
- Ensure the chapter 2 source scene supports the retcon, or show the author's source edit explicitly.
- Know the actual expected affected/checked/changed counts. Never use a hard-coded success counter.
- Increase browser text size until the quoted violation and diff are readable in the final recording.
- Hide credentials and unrelated tabs. Keep model and runtime labels visible.
- Rehearse twice with the real engine. Record elapsed model time and plan the edit around that observation.

## Plugin-first opening

For the current build, briefly establish that one installed package supplies the writer and DAG bundle, then begin in Airflow: **Browse → RETCON writer → Settings**. Show the model ID, the empty key field indicating a saved server-side key, and the Test/Save controls. Then stay in the embedded writer for the cascade. Describe it as a complete Airflow-hosted application; the key/model are an Airflow Connection, not handwritten environment setup. Keep the credential field blank in the recording.

## Measured rehearsal

An earlier embedded-plugin rehearsal on Airflow 3.1.8 reached review in **1:36**, with both repairs passing first try. The earlier verified native OpenRouter run took **2:14 from the asset-triggered start to the review gate**, including model retries and one rejected incomplete paragraph. Condense that wait with an on-screen **“Elapsed time condensed · actual model + validation: 2m 14s”** caption. Preserve the real causal order. Browser approval then resumed Airflow and published successfully. These are historical timings, not measurements of the Airflow 3.3 package. Rehearse the installed package and replace the caption with that run's actual elapsed time. See [verification evidence](VERIFICATION.md). Do not promise a subminute live free-model run.

## Main take

| Time | Screen and action | Voiceover |
| --- | --- | --- |
| 0:00–0:12 | Aster manuscript, chapter list, visible story facts. | “Every data engineer knows backfill. Novelists call it retcon. Change the past, and every later scene has to survive the change.” |
| 0:12–0:27 | Briefly show draft import/paste and the readable editor, if verified. Return to Aster. | “RETCON is for writers. Bring a draft, inspect its story facts, and keep control of the text. You don't need to learn Airflow.” |
| 0:27–0:43 | Set Mara's death boundary to the end of chapter 2; show the proposed canon change. | “Mara dies at the end of chapter two. This revision tells us which scenes need checking. A mention alone does not mean a rewrite.” |
| 0:43–0:59 | Submit. Show the impact view with explicit reasons, then the actual run link. | “RETCON resolves the story dependencies. Airflow orchestrates the work and records every step.” |
| 0:59–1:18 | Open a failing chapter; highlight the exact post-death dialogue and rule explanation. | “Here is the break: Mara speaks after her death. This deterministic rule checks attributed dialogue against the new canon, with the offending passage attached.” |
| 1:18–1:34 | Show affected-but-valid chapter and unchanged status. Briefly reveal actual Airflow tasks. | “This chapter also references Mara, but its scene still passes. It stays untouched. The workflow only proposes repairs where the checks fail.” |
| 1:34–1:59 | Show real repair completion and before/after passage. Scroll only enough to show preservation. | “The model receives the failing scene and the new fact. RETCON validates the proposed patch and rechecks it. These surrounding passages are preserved.” |
| 1:59–2:18 | Click approve; show accepted revision and the corresponding run state. | “A passing check is not permission to publish. I review the change and decide whether it becomes canon.” |
| 2:18–2:35 | Show actual counts and export the manuscript. | “Two paragraphs repaired. Three chapters completely untouched. No remaining violations of the rules we checked. And the writer still has the final say.” |
| 2:35–2:45 | Title card, repository URL, category. | “RETCON. Backfill for stories. Built with Airflow, directed by the writer.” |

If import, export, or native HITL has not been verified, shorten those beats and say only what the implementation supports. The main action must remain real Airflow execution for the recommended wildcard category.

## Important wording corrections

| Tempting line | Use this instead |
| --- | --- |
| “Airflow knows which paragraph mentions Mara.” | “RETCON's lineage index identifies affected scenes; Airflow runs the repair workflow.” |
| “Editing the YAML automatically fires the DAG.” | “Saving this canon revision emits an asset event” — only if that path is implemented and observed. Otherwise say “starts a run.” |
| “Only two chapters were touched.” | State the stored actual count, and account separately for an author's source chapter edit. |
| “Zero continuity errors.” | “No remaining violations of the rules we checked.” |
| “The AI fixed the story.” | “The model proposed a repair, the checks passed, and the writer approved it.” |
| “A native Airflow human-in-the-loop step.” | Use only when an actual HITL operator waits and resumes. An app approval is described as an application review gate. |
| “This is Airflow backfill.” | “This is backfill for stories” unless Airflow's actual backfill API is part of the demonstrated path. |
| “Live” over an edited wait. | Label “Elapsed time condensed” and show the genuine run ID and elapsed time. |

## Showing the red moment truthfully

The story contradiction should be red in the writer UI. That does not require crashing the Airflow validation task. A task can succeed at producing a findings report while the report contains a failed data-quality rule.

If the implementation deliberately uses an Airflow task failure to represent a gate, show its real failed state and actual recovery path. Do not color a successful task red or claim an exception occurred to improve the shot.

Prefer one clear failure to a wall of logs. Show:

- Chapter and scene.
- The canon fact and its effective time.
- The exact violating quote.
- Rule name in plain language.
- Proposed correction and recheck result.

## Free-model latency and failure plan

Do not put all five first-draft generations inside the video. Prepare the synthetic baseline before recording and say it is the supplied sample.

Record the full real cascade. If the model takes longer than the time budget, cut the waiting period and label it clearly; preserve the causal order, run ID, and actual output. A recorded successful run is acceptable demo evidence when presented as a recording, not a live event.

If the free endpoint fails, show the real “Needs attention” state and the retained original. Demonstrate manual repair plus a real recheck if supported. Do not silently switch models, substitute canned output while showing a live label, or animate success. A transparent completed recording of an earlier successful run can be used with its actual timestamp/model information.

## Three screenshots worth keeping

1. Impact preview: one canon change, affected scenes, and preserved control.
2. Evidence and diff: the dead-character line beside the constrained proposed repair.
3. Execution and approval: a real Airflow run identifier plus the writer's accepted revision.

The viewer should be able to understand the project from these three images even with audio muted.

## Judge questions to rehearse

**How do I install it?**

“Install the wheel in Airflow 3.3, register its DAG bundle once, and restart Airflow. The plugin supplies the workspace, and Airflow discovers its two packaged DAGs. Writers then configure a model and key in the UI.”

**Why Airflow?**  
“Each revision is a reproducible workflow with explicit inputs, evidence, retries, and a publication gate. The writer gets a simple interface; Airflow gives us durable orchestration and inspectable execution.”

**Isn't this already in writing tools?**  
“Story bibles, contextual generation, and timelines already exist. Our focus is a visible revision transaction: determine impact, check existing scenes, propose only needed repairs, then obtain approval.”

**Can it catch every contradiction?**  
“No. This prototype enforces specific rules on structured scene facts. It links evidence to prose and sends unresolved or ambiguous cases to the writer.”

**Who creates the lineage?**  
“RETCON does. The sample has explicit scene facts and dependencies. General draft extraction needs validation because models and name matching can miss context.”

**What if the model fails?**  
“The original remains intact. Attempts are capped; the run records the error and asks for attention rather than publishing an unchecked rewrite.”

**Can I use my own draft?**  
Answer from the verified build: describe exact formats, splitting rules, editing/export support, and whether extracted facts need manual review. Never generalize a curated sample into support for arbitrary novels.

## Recording and submission checklist

- Script is aligned with actual code and runtime evidence.
- Final duration is 2:45 or less; important content is never after 3:00.
- Text is legible at ordinary playback size.
- Waiting-time edits are labeled.
- No credentials, invented telemetry, or unimplemented controls appear.
- Public repository has local instructions, a license, and known limitations.
- Public video opens without an account requirement.
- Written description states the category, Airflow features actually used, implementation, and hardest problem.
- Resolve the deadline discrepancy described in [JUDGE_BRIEF.md](JUDGE_BRIEF.md) with organizer information before treating submission timing as confirmed.
