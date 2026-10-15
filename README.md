# OSCAL — public copy-and-run workbench

## Seven-object PREVIEW value/FACT QA — current (October 15, 2026)

**Corrected QA after singleton-parent false positive (October 15, 2026):**
The owner's first QA run stopped with `WRONG_PROPERTY_PARENT_INSTANCE`.
The previous QA erroneously equated a child's `PARENT_INSTANCE_KEY` with
the parent's `INSTANCE_KEY`, which is not the actual SSP registry contract.
The maintained mapper creates the one `system-characteristics` `object`
parent with `INSTANCE_KEY="singleton"`, stores **NULL** for child
`PARENT_INSTANCE_KEY`, and resolves correct ownership through the
unique-parent `CONTAINS` FACT edge. The public QA file linked below was
**replaced and read-back verified** in GitHub at commit
`041dfcffdcb8e446b7ef68999287d65d0a392b13`, blob
`8c9525533eb63a345383b75755ee6a76b6ca4d3c`. Its updated fixture
and independent tests exercising REAL maintained Cells 3/4/5 passed
**13/13** focused tests (overall broad CI retains 28 historic failures
and 88 historic errors). **The mapper, approved mapping CSV and Snowflake
PREVIEW have NOT been changed by the QA correction.** Use the CURRENT link,
not the old copy from an earlier Snowflake cell. The corrected QA has not
yet been executed in Snowflake.

The owner-provided Snowflake DEV screenshot shows **Source One SSP PREVIEW COMPLETE**:
2,813 source records; 879,640 candidate DIM nodes; 876,827 candidate FACT
edges; **50,634 proposed DIM inserts and 50,634 FACT inserts**;
0 updates, 0 lineage gaps and **no target writes or COMMIT**.

[**OPEN THIS ONE NEW PYTHON CELL — Source One SSP seven-object source-to-PREVIEW value/FACT QA**](notebooks/source-one-ssp-seven-object-preview-value-parity-readonly.py).

**Copy the entire linked GitHub file and paste/run it as ONE NEW Python cell
in the SAME successful Snowflake DEV notebook session. Do not rerun Cells 1–7,
the earlier preview runner, registry SQL or COMMIT.**

The cell checks both possible cached PREVIEW containers (standard Cell 7
`MODEL_GRAPHS/PIPELINE_REPORT`, or the seven-field temporary overlay
`SSP_OBJECT_PREVIEW_GRAPHS/SSP_OBJECT_PREVIEW_REPORT`) against the *exact*
owner screenshot counts. It reports which preview ran and whether the
currently staged Notebook Files CSV matches the authoritative GitHub file
blob. Then it compares all seven Object-to-JSON-text properties for **up to 15
same-source-record samples**, including omitted and explicit-null cases,
and checks each sampled property node's actual one-parent FACT containment.
All 2,813 source records are profiled for coverage. This is READ ONLY,
prints only counts and field names, no Archer business values/Content IDs.

**Return these lines:** `PREVIEW_VARIABLE_SOURCE`,
`MAPPING_INPUT_SCOPE`, `NOTEBOOK_FILES_CSV_BLOB`,
`SAMPLED_FIELD_VALUE_MISMATCHES`, each `FIELD_QA` line and `RESULT`.
If stopped or mismatched, send that result; do **not** COMMIT.

**Important:** The approved PREVIEW validates graph shape and prospective
changes, not actual field-by-field value equality or a physical COMMIT.
If the preview was temporary overlay, stage the reviewed updated 168-rule
private CSV and repeat a file-loaded PREVIEW/value QA before authorizing
any target write. The 50,634 proposed inserts may include other newly
approved package fields; they are not proved to arise solely from the seven
object fields.

[Current project checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-15-source-one-ssp-object-preview-passed-50634-inserts-qa-next.md).

---

## Previous step — SSP seven OBJECT-valued properties corrected PREVIEW (completed)

**First, open the [updated maintained Cell 3 (private OSCAL GitHub)](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/03_canonical_mapping_contract.py).** Copy its entire Python code into the existing Cell 3 of the already-open Snowflake DEV `NB_ARCHER_OSCAL_MAPPER_V2` notebook and execute **that Cell 3 only**. Do not rerun Cell 1, Cell 2, or the previous failed Cell 7. This refreshes the reusable null-preserving `json-text` compiler support in the current Python session; it does not read sources or write targets.

**Second, open [Source One SSP 168-row seven-object PREVIEW-only runner](notebooks/source-one-168-object-props-preview-only.py).** Copy the complete file into **one NEW Python cell in the SAME notebook session** and execute once. It reuses frozen Source One inputs, checks the owner's previous exact mapping fingerprint and the seven original `direct` rules, builds a temporary **in-memory** seven-rule `json-text` overlay, recompiles the SSP metadata, and requests exactly **one PREVIEW** with writes disabled. It does not reload raw data, replace the notebook's uploaded CSV, run the registry SQL, or COMMIT.

The corrected **authoritative** CSV is already saved privately on `simplify-metadata-boundary`, **168 mapping records**. It includes the new `json-text` transforms and keeps `NULL_POLICY=preserve` for seven populated OBJECT-shaped Archer fields. All 50 Control Implementation mappings remain APPROVED, and the five Source One and native requirement/assessor behavior outside the seven edits is unchanged.

**Report only:** `SOURCE_ONE_SSP_168_OBJECT_JSON_TEXT_PREVIEW_ONLY`, `CANDIDATE_MAPPING_FINGERPRINT`, `PREVIEW_STATUS`, `EXPECTED_CHANGES`, and `RESULT` (or any STOP/error). No source values/Content IDs needed.

**Do not COMMIT.** This is a no-write *candidate overlay* PREVIEW to isolate the corrected transforms. Before later COMMIT, the reviewed authoritative CSV must actually be staged in Notebook Files and an exact file-loaded DEV PREVIEW/source-value QA accepted. The source's earlier value-based identity/obsolete-row guard is still active. A successful GitHub code test is not a Snowflake acceptance run.

[Previous 168-row scalar-shape diagnostic (owner ran: seven OBJECT fields, 17,727 shape errors)](notebooks/source-one-ssp-scalar-shape-readonly.py).

---

## Earlier SSP scalar shape diagnostic — completed (2026-10-15)

[**OPEN: Source One SSP scalar-property shape diagnostic — COPY/PASTE/RUN**](notebooks/source-one-ssp-scalar-shape-readonly.py)

The owner uses GitHub as the copy-and-run surface. **Do not ask them to download conversation attachments or scripts.** Open this public GitHub Python file, copy all its contents and paste into **one NEW Python cell** in the existing Snowflake DEV `NB_ARCHER_OSCAL_MAPPER_V2` notebook session where the SSP PREVIEW failed with `Property value must be scalar`.

The script uses the already cached Source One source snapshot and selected 168-field mapping rules; it checks exact release and no-write flags. It reports only field names, source shapes, transforms and aggregate counts, **never business payload values or Archer Content IDs**. It does not query Snowflake separately, rebuild the graph, change the CSV, create registry rows, or write DIM/FACT.

**Do not rerun Cells 1–7, a previous COMMIT, or the CATALOG preview.** If the notebook was restarted, report the missing-cache stop message rather than blindly rebuilding or committing. Send back `SCALAR_SHAPE_ERROR` lines and the `RESULT` line. We will classify confirmed non-scalar field shapes and propose reviewed, source-preserving mapping transforms without excluding the fields.

[Current authoritative private/controlled Source One 168-field mapping CSV](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/ARCHER_OSCAL_MAPPINGS.csv). Historical 161-row checkpoint is superseded for inventory only. **No new SSP COMMIT evidenced.**

---

## Previous Source Two Topic/Section QA — reference only

**Earlier Source Two checkpoint: 2026-10-15.** Source Two Authoritative Sources — independent Archer CURATED_JSON → OSCAL native property QA for **four new Topic/Section fields**.

## Previous Source Two one-cell QA

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
