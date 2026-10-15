# OSCAL public copy-and-run workbench

**Current step — October 15, 2026:** one read-only source inventory for the **next Topic and Section Catalog mapping batch**. The last six-field Sub-Section batch already returned `COMMITTED_AND_VERIFIED` in owner Snowflake DEV; **do not run the older guarded COMMIT cell again**.

## Current runnable

[**Topic + Section — next field profile (Python)**](notebooks/source-two-topic-section-next-field-profile-readonly.py)

Open the link, copy its **entire code**, paste into **one new Python cell** in the existing `NB_ARCHER_OSCAL_MAPPER_V2` Snowflake DEV notebook session, and run **only that new cell**.

This reads the cached `SOURCE_INPUTS["source-two-source"]["lookups"]["joined_sources"]` Topic and Section `CURATED_JSON`. It checks five additional scalar/prose mapping candidates plus one separately deferred criticality-rollup diagnostic, verifying source field population and shapes in one pass. Expected current scopes: 1,416 Topics and 10,566 Sections. **Outputs only aggregate counters and candidate statuses.** It does not print payloads, Content IDs, SQL table names, or source values.

**Do not** rerun the seven original mapper cells, any earlier Source Two PREVIEW/COMMIT, registry SQL, or the old six-field QA. If cache/session is missing, send the exact error and stop. Field source population is **not** mapping approval or a target PREVIEW.

## Mapping candidates being profiled

Topic `DOCUMENT_NUMBER` → `catalog.groups[].props[document-number]`; Topic `TOTAL_NUMBER_OF_SECTIONS` → `catalog.groups[].props[section-count]`. Section `SECTION_SHORT_DESCRIPTION` → `catalog.groups[].groups[].props[short-description]`; Section `TOTAL_NUMBER_OF_SUB_SECTIONS` → `catalog.groups[].groups[].props[sub-section-count]`; Section `INFORMATION` → `catalog.groups[].groups[].parts[information].prose`. Section `SUM_OF_SUB_SECTION_CRITICALITY_VALUE` is **diagnostic only** pending owner semantics/path and is not enabled for mapping.

The proposed Catalog paths follow existing mapped Topic/Section group ownership. The original review workbook has clipped paths for some of these fields. Any populated candidates need exact path/transform owner review before an additive no-target-DML PREVIEW.

## Public/private boundary

The public workbench retains only this active Python step, the README and a separately requested Change Control SQL diagnostic, which is not part of Source Two and remains untouched. Old completed runnable versions stay recoverable via Git history. Keep mapping CSVs, full engineering decisions, source payloads, screenshots and dated checkpoints in restricted project storage; confirm the source repository is actually private before uploading confidential material.

**No source, registry, DIM or FACT target writes, and no COMMIT** are performed by this profiler.
