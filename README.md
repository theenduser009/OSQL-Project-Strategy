# OSCAL — public copy-and-run workbench

**Current step: 2026-10-15.** Source Two Authoritative Sources — independent Archer CURATED_JSON → OSCAL native property QA for **four new Topic/Section fields**.

## One new Python cell — run now

[**Open current Source Two four-field RAW parity QA**](notebooks/source-two-topic-section-next-four-raw-parity-readonly.py).

Copy **the entire Python file** into **one new Python cell directly after the successful Topic/Section PREVIEW in the same active Snowflake DEV notebook session**. Run **only the new QA cell**. The previously executed preview variables must still exist as `NEXT_TOPIC_SECTION_GRAPHS` and `NEXT_TOPIC_SECTION_REPORT`.

**Do not rerun earlier Cells 1–7, registry SQL, source profiling, the successful PREVIEW, or any COMMIT.** No need to change the already uploaded 67-row mapping candidate.

The QA independently matches **1,416 original Topic Content IDs and 10,566 original Section Content IDs** to their respective PREVIEW group elements using the embedded `archer-content-id` provenance property; it checks each exact destination value:

- Topic `DOCUMENT_NUMBER` → `catalog.groups[].props[name=document-number].value`, verifying **13 populated text** and **1,403 omitted JSON-null** records.
- Topic `TOTAL_NUMBER_OF_SECTIONS` → `catalog.groups[].props[name=section-count].value`.
- Section `SECTION_SHORT_DESCRIPTION` → `catalog.groups[].groups[].props[name=short-description].value`.
- Section `TOTAL_NUMBER_OF_SUB_SECTIONS` → `catalog.groups[].groups[].props[name=sub-section-count].value`.

It confirms the approved Sub-Section and graph scope remained unchanged (33,679 DIM, 33,531 FACT; **11,982 proposed Topic/Section DIM updates; zero new inserts/FACT changes**), checks correct Source→Topic→Section ownership and that deferred Section `INFORMATION` was not emitted. It outputs only counts, not original payload text or record IDs.

**Output to return:** `SOURCE_TWO_NEXT_FOUR_TOPIC_SECTION_ORIGINAL_RAW_FIELD_QA`, four per-field counts, `FIELD_MISMATCHES_TOTAL`, `RAW_TEXT_SPACING_DIFFERENCES_DIAGNOSTIC`, `RESULT`.

A successful transformed-value comparison ends `RESULT: PASS_FOUR_FIELD_SOURCE_TO_TRANSFORMED_TARGET_PARITY` and `FIELD_MISMATCHES_TOTAL: 0`. The script separately reports source-to-stored spacing differences for the two text properties; those require an informed source-owner disposition if nonzero. **Source-value QA and owner target-path acceptance are not the same as a target COMMIT.**

**Read-only:** no SQL, target writes, mapper reruns, registry edits or COMMIT. If it prints an error, stop and share the aggregate output/traceback; don't rerun COMMIT.

## Repository boundaries

Full mapping CSVs, test fixtures, checkpoints, and all project decisions are maintained in the OSCAL source-of-truth project. [67-row review candidate](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/release_candidates/2026-10-15-topic-section-next-four/sources_source_runtime.csv). Verify that repository's actual GitHub visibility before adding confidential content.

Only this current QA runner supersedes the old four-field PREVIEW runner. **Other Source One Python/SQL artifacts and the existing Change Control SQL in this public repo were preserved untouched**, because their completion/disposition is not part of this request. Removed completed runners remain recoverable from Git history.
