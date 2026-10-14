# OSCAL public copy-and-run workbench

**Current next step — 2026-10-14:** validate the **six newly mapped Source Two Authoritative Sources Sub-Section fields** against the original `CURATED_JSON` and the successful **no-target-DML** CATALOG DEV PREVIEW.

## Copy and run exactly ONE new Python cell

[**Open the current six-field original-source parity QA**](notebooks/source-two-subsection-next-six-exact-raw-parity-readonly.py)

Copy the **entire Python file** into **one NEW Python cell** directly beneath the successful six-field CATALOG PREVIEW in `NB_ARCHER_OSCAL_MAPPER_V2`, **in the same active Snowflake DEV notebook session**. Run **only this new cell**. It uses the retained `NEXT_SOURCE_TWO_CATALOG_GRAPHS`, `NEXT_SOURCE_TWO_CATALOG_REPORT` and original source lookup frame; there is **no requirement to rerun Cells 1–7, the prior eight-field profiler, the last PREVIEW or registry SQL**.

The QA compares original Archer Sub-Section `CURATED_JSON` values against the exact native `METADATA_JSON.parts[overview].prose` or `props[name].value` output for six newly enabled mappings. It checks all 20,000 original child Content IDs, exact target-parent Sub-Section grain, absent source values versus absent target values, duplicate props/parts, and exclusion of four deferred fields.

**Output to send back:** `SOURCE_TWO_NEXT_6_INDEPENDENT_CURATED_JSON_FIELD_QA`, six per-field count summaries, `FIELD_MISMATCHES_TOTAL`, `RAW_DIRECT_PROSE_DIFFERENCES`, and `RESULT`.

**Expected, but not yet verified live:** `PASS_EXACT_SIX_FIELD_SOURCE_PARITY`; 19,962 source descriptions; 0 mismatches and 0 direct-prose/raw differences. If the cell raises an exception or reports discrepancies, stop and share the aggregate error/status. Do not COMMIT or rerun accepted loads.

The script is **read-only**: it does not invoke the mapper, registry SQL or a target loader, contains no client-specific database namespace, prints no business content or Content ID values, and does not modify DIM/FACT. Its focused tests passed 8/8 in private CI; broad CI continues to have historical failures.

## Public/private file policy

The public main branch keeps only **this one current runnable and README**. The finished PREVIEW-only script is retired from main, but recoverable through Git history. The 62-row mapping CSV, all underlying source metadata, screenshots, field decisions, tests, and dated checkpoints remain in the private OSCAL source-of-truth repository. **No client-specific mapping workbook or business data belongs in this public workbench.**

Workflow: private design → sanitized public run cell → owner DEV validation → dated private checkpoint → retire public runnable when complete.
