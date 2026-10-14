# OSCAL — public copy-and-run workbench

**Purpose:** This public repository contains only the currently requested, minimal **read-only Snowflake runnable**. The project's code, mappings, QA evidence, decisions, and historical checkpoints belong in the separate OSCAL source-of-truth project and its restricted GitHub repository **once that repository's private visibility is verified**.

## Run now — Source Two Sub-Section prose fields

[Open the read-only Python cell](notebooks/source-two-subsection-two-parts-profile-readonly.py).

Copy the **entire file** into **one new Python cell** in your connected Snowflake DEV notebook, then run only that cell. Send the aggregate `SOURCE_TWO_NEXT_SUBSECTION_PARTS_READ_ONLY_PROFILE` result back for review.

It profiles only `SUB_SECTION_DESCRIPTION` and `INFORMATION` in Authoritative Sources Sub-Section `CURATED_JSON`. It uses Snowflake table metadata to locate one unambiguous RAW table; if none or more than one is accessible, it stops without guessing. It does **not** run the seven-cell mapper, change registry entries, or write to DIM/FACT targets. These two mappings are **candidate only**, not committed.

## How we keep the public workbench clean

- Exactly one current runnable is retained; old finished or paused SSP, Assessment Results, and Control Standard scripts were removed from the active branch on **2026-10-14**. They remain recoverable from Git history and can be republished **only when needed again**.
- When the current runnable is completed, replace it with the **next approved copy-and-run task**, rather than accumulating scripts and duplicated guides.
- **Never commit:** credentials, database namespace identifiers, business record IDs/values, source JSON/payloads, screenshots, account-specific results, full mapping workbooks, or confidential project checkpoints.
- Deleting paths from this branch does **not** erase previous public Git history. Sensitive historical exposure, if any, must be assessed separately.

**Workflow:** Review and maintain in the restricted project → publish sanitized single runnable here → copy/run in DEV → return aggregate results → record the verified checkpoint back in the restricted project → retire the public runnable.
