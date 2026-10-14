# OSCAL — public copy-and-run workbench

**Current step (October 14, 2026): independent original Archer RAW parity QA for the six new Source Two Sub-Section mappings.** The owner has already run the corrected `prose-direct` DEV PREVIEW; it passed with 33,679 DIM nodes / 33,531 FACT relationships, exactly 20,000 proposed DIM payload updates, zero inserts, zero FACT updates and **no target DML**.

## Run exactly ONE new Python cell now

[**Open current six-field exact original-RAW QA**](notebooks/source-two-subsection-next-six-exact-raw-parity-readonly.py).

Copy the **entire file** into a new Python cell directly under the successful corrected PREVIEW in your **same active Snowflake DEV notebook session**. Run **only this new cell**.

The script reads the current in-memory `NEXT_SOURCE_TWO_CATALOG_GRAPHS` / `NEXT_SOURCE_TWO_CATALOG_REPORT` pair from the standalone preview. It also supports regular Cell 7 `MODEL_GRAPHS` / `PIPELINE_REPORT` **only if** that pair contains the six new mappings with the required `prose-direct` transform and a matching compiled fingerprint. Historical `text`-transform Cell 7 candidates are rejected; when both current and stale graphs exist, the current `prose-direct` candidate wins. Two different valid-looking corrected graphs trigger a review error instead of a guess.

It compares each of the six new mapping values to original retained Sub-Section `CURATED_JSON`, checks the original child Archer Content ID provenance, and verifies `parts[overview].prose` directly against the unchanged source text, **including surrounding whitespace**. It separately counts unpopulated values and confirms that four deferred fields are not materialized.

**Send back:** `SIX_FIELD_QA_PREVIEW_SOURCE`, the six field counters, `FIELD_MISMATCHES_TOTAL`, `RAW_DIRECT_PROSE_DIFFERENCES` and `RESULT`.

Successful live acceptance requires `RESULT: PASS_EXACT_SIX_FIELD_SOURCE_PARITY`, `FIELD_MISMATCHES_TOTAL: 0`, `RAW_DIRECT_PROSE_DIFFERENCES: 0`. These are **expected**, not yet live verified. If the cell raises an error, send its printed aggregate diagnostics. **Do not rerun prior Cells 1–7, registry SQL, PREVIEW or COMMIT.**

## Publication boundary

This PUBLIC workbench contains sanitized current Python QA, this README and the previously provided **unrelated** `sql/change-control-dim-archer-trace.sql`, which was preserved. The earlier corrected PREVIEW runner was retired from public main, but remains recoverable through Git history. Full mapping CSVs, sensitive source details, tests and historical checkpoints should remain in the restricted OSCAL source of truth. GitHub repository visibility should be verified separately before assuming restricted access.

No client namespace, source payload value, credentials or business record IDs are embedded in the QA code. No DIM/FACT writes or mapper execution are performed by this script.
