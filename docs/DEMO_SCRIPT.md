# RETCON demo — 2 minutes 45 seconds

**Pitch:** Every data engineer knows backfill. Novelists call it retcon.

## Prepare

Start the Airflow 3.3 demo, open RETCON, configure the OpenRouter connection, and reset the Aster sample. Keep the key hidden. Record the real workflow; label any shortened wait as “Elapsed time condensed.”

## Record

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00–0:15 | RETCON inside Airflow | “Every data engineer knows backfill. Novelists call it retcon.” |
| 0:15–0:30 | Settings, then the manuscript | “Install one plugin, connect a model, and bring your draft. Writers stay in this workspace.” |
| 0:30–0:45 | Select Mara, death after chapter 2 | “What if Mara dies here? Which later chapters need to change?” |
| 0:45–1:05 | Inspect the impact | “Three chapters reference her. Only two contain contradictions.” |
| 1:05–1:25 | Quoted dialogue violations | “A dead character speaks. This is a deterministic data-quality failure.” |
| 1:25–1:45 | Airflow run and preserved chapter 5 | “An asset event starts the workflow. A memory of Mara remains valid, so it stays untouched.” |
| 1:45–2:10 | Paragraph diffs | “The model repairs the failing paragraphs. RETCON validates the replacements and preserves the surrounding text.” |
| 2:10–2:30 | Approve, then export | “A passing check does not publish the story. The author decides.” |
| 2:30–2:45 | Result and repository | “Two paragraphs repaired. Three chapters unchanged. RETCON: backfill for stories.” |

## Keep the claims precise

RETCON identifies story dependencies; Airflow orchestrates the declared workflow. Report the checks that passed, not perfect narrative consistency. Use actual counters and generated output. If the model fails, the manuscript remains intact and the UI shows the failure.
