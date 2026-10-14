# OSCAL public copy-and-run workbench

**Current work (October 14, 2026):** guarded Snowflake **DEV PREVIEW** of six new Authoritative Sources Sub-Section Catalog payload mappings. No target COMMIT authorized.

## Before copying the public runnable

Obtain the current staged **62-row** `sources_source_runtime.csv` from the **restricted OSCAL source-of-truth**. It preserves the 52 already committed mapping rows, enables six new PREVIEW candidates (`SUB_SECTION_DESCRIPTION` plus five passing scalar fields), and defers four fields (`INFORMATION`, `SUBSECTION_CRITICALITY_VALUE`, and two `TIMESTAMP_NTZ` dates).

In your original Snowflake DEV notebook, replace only its Notebook Files `sources_source_runtime.csv` with that private 62-row file. This replacement alone does not execute mapping or write any database tables. The previously accepted **52-row mapping state must still be loaded in the active notebook session** so this gate can compare the prefix.

## Copy and run ONE Python cell

[Open the current Source Two guarded PREVIEW-only cell](notebooks/source-two-subsection-next-six-preview-only.py).

Copy the **entire file** into **one NEW Python cell** below the completed seven-cell Source Two notebook and run only the new cell.

The script checks the exact unchanged 52-row mapping prefix and 10 appended active/deferred rows, compiles through the existing generic mapper and calls `PREVIEW` explicitly regardless of a previous `OSCAL_LOAD_MODE` setting. It blocks wrong model/registry scope, changed mappings, and unexpected new DIM/FACT keys or FACT updates. It does **not** write target DIM/FACT tables or COMMIT; the existing PREVIEW loader may make temporary tables.

Expected output includes `SOURCE_TWO_NEXT_6_CATALOG_SUBSECTION_PREVIEW`, then `PREVIEW_RESULT: PASS_NO_TARGET_DML; FIELD_VALUE_QA_AND_OWNER_REVIEW_PENDING` if all checks pass. Actual DIM payload-update count is reported live, not guessed.

If the script raises `MATCHING_ACCEPTED_52_NOTEBOOK_SESSION_REQUIRED` or `SOURCE_TWO_NEXT_SIX_PREVIEW_BLOCKED_`, **STOP** and share the error; do not blindly re-run past COMMIT cells or registry SQL.

## Public/private separation

This PUBLIC repo intentionally holds **only the current sanitized runnable and this README**. The completed 8-field profiler is retired from the branch but recoverable through Git history. Full mapping CSVs, field-level data, tests, owner decisions, screenshots and dated checkpoints stay in the PRIVATE OSCAL project. No company-specific fully qualified table identifiers or business record values are printed or committed here.

**Workflow:** private mapping design → public runnable → owner DEV PREVIEW → private checkpoint → next public runnable. PREVIEW does not authorize COMMIT.
