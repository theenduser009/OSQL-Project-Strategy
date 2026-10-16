# OSCAL — public copy-and-run workbench

## CURRENT — Source Two CATALOG compiler and nested hierarchy restored (2026-10-16)

**Owner Snowflake issue (same notebook, no other notebook):** CATALOG
PREVIEW stopped `FAILED_BEFORE_COMMIT` because the Source Two 67-row
mapping file includes `oscal-token` and `prose-direct`, but
the previously shared Cell 3 did not register them; Cell 1 also lacked
the earlier accepted Topic→Section→Sub-Section joined RAW bindings.
52 Catalog rows were blocked by the compiler, no DIM/FACT writes.
The existing 67-row `sources_source_runtime.csv` is ALREADY in
the owner's Notebook Files; **do not request another upload**.

**Fixed in existing shared seven-cell production code (not another runner):**

- [Maintained Cell 1](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/01_initialization_and_configuration.py)
  — restored Source Two joined lookup contracts and hierarchy; after
  pasting, set `SELECTED_MODELS=("CATALOG",)` (Git source defaults SSP).
- [Maintained Cell 3](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/03_canonical_mapping_contract.py)
  — restored approved ID and narrative transforms without losing Source
  One's JSON-text null-preservation.
- [Maintained Cell 4](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/04_parsing_transform_payload_helpers.py)
  — restored exact original Sub-Section prose, token normalization and
  accepted group-parent/source-ID relationships.

**ONE owner next action:** replace only Cells **1, 3 and 4** with
complete linked GitHub code in `NB_ARCHER_OSCAL_MAPPER_V2`, set
`("CATALOG",)` and run existing Cells **1 through 7 in order** in
`PREVIEW` only. Cell 2 must refresh lookups. Do not run Source
One SSP COMMIT again or either earlier committed Catalog batch.
After owner-run PREVIEW, check against previous approved four Topic/
Section properties: 11,982 planned DIM updates, zero FACT changes.
No additional QA runner or COMMIT until normal PREVIEW succeeds.

**GitHub verification:** [Actions 38916790804](https://github.com/theenduser009/Oscal-mapping-strategy/actions/runs/38916790804):
5/5 new focused tests PASS, generated notebook check PASS;
full suite historical 28 FAIL / 88 ERROR with zero new failing identities.
Source One 168 mapping rows and Source Two candidate 67 rows both unchanged.
**Code verified in GitHub; new integrated code NOT yet run in Snowflake.**

[Latest dated OSCAL source-of-truth checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-shared-v17-joined-transform-compatibility-restored.md).

---

## Source One SSP physical COMMIT accepted (2026-10-16)

**New owner Snowflake evidence:** The earlier, exact-count guarded Cell 7
was executed with `mode=COMMIT` and returned top-level
`COMMITTED_AND_VERIFIED` for `source-one / SSP`:
**50,634 DIM inserts and 50,634 FACT inserts, zero updates and
zero retirements**, `writes_executed=true`,
`persisted=true`, `committed=true`, 0 lineage gaps,
2,813 original records, 879,640 nodes and 876,827 edges.
This is **the completed DEV batch**, not a pending PREVIEW.
The loader's verified status confirms post-COMMIT validation completed;
individual nested verification counters are cropped in the screenshot.

**Next code-alignment step:** Paste the
[current generic production Cell 7](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/07_mapper_orchestrator.py)
over the older pinned Cell 7. Keep the default `PREVIEW` mode.
**Do not rerun the completed COMMIT** and do not rerun unchanged Cell 6
merely for this code update. The generic Cell 7 no longer hardcodes
2,813 sources, 50,634 inserts or the old release fingerprint.
All 168 mapping rows remain unchanged.

[Latest owner-run Snowflake COMMIT checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-one-ssp-50634-dim-fact-owner-commit-readback.md).

---

## Generic Cell 7 architecture — accepted production source (2026-10-16)

**Owner architectural decision:** Daily Archer-to-NIST OSCAL runs must not
require yesterday's source count, graph node/edge counts, mapping
fingerprint, or expected insert totals in production Python. The
one-off `OSCAL_COMMIT_APPROVALS` dictionary and its special route gate
were removed from the existing **Cell 7**, restored to previously
verified generic orchestration. **Cell 6 remains unchanged** with
transactional preflight, obsolete-row blocking, rollback and post-COMMIT
readback; exact expected counts can be optionally supplied in approved
runtime configuration for a particular deployment.

**[Open CURRENT complete generic Cell 7 source in OSCAL GitHub](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/notebooks/cells/07_mapper_orchestrator.py).**
Copy the complete file directly from GitHub to the existing Cell 7.
There is **no new runner and no need to re-run unchanged Cell 6**
merely to align the notebook source. Keep `OSCAL_LOAD_MODE = "PREVIEW"`
until the last executed Cell 6/7 result and any pending warehouse
COMMIT outcome are confirmed. Do not blindly rerun COMMIT.

**Verified GitHub change:** source commit
`7fa19eaeb79b25b109ad0246d6b8faca755c4192`;
6/6 focused generic/CSV-preservation tests PASS and generated
notebook check PASS in [CI 38906325754](https://github.com/theenduser009/Oscal-mapping-strategy/actions/runs/38906325754).
Historical broad CI still reports 28 FAIL / 88 ERROR with no new
failing case identities. Source One mapping CSV untouched at **168 rules,
165 approved, all 50 Control Implementation approved**. Previous
owner DEV PREVIEW/QA for that previous run remain accepted but are NOT
a new physical COMMIT/readback.

**Superseded by the newer owner screenshot above:** The earlier
exact-count guarded Cells 6/7 did complete a physical SSP DEV COMMIT and
returned `COMMITTED_AND_VERIFIED`. Do not repeat that batch.

[Latest dated source-of-truth checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-generic-cell7-restored-no-hardcoded-approvals.md).

---

## Prior step — completed GitHub CSV semantic reconciliation (October 15, 2026)

**Accepted owner Snowflake result:** Source One SSP seven-object QA
`PASS_SAMPLED_SEVEN_FIELDS_SOURCE_TO_GRAPH_AND_PARENT_FACT`, **15 source IDs,
105/105 matched source-field property values, 105 correct containment FACT
edges, 0 field mismatches**; 2,813 original Source records profiled.
`PREVIEW_VARIABLE_SOURCE=STANDARD_CELL7_PREVIEW`,
`MAPPING_INPUT_SCOPE=CACHED_168_JSON_TEXT_RULES`, zero target DML.
**Remaining discrepancy:** `NOTEBOOK_FILES_CSV_BLOB=FILE_DIFFERS_FROM_CURRENT_GIT_CSV`.
This may reflect notes or formatting; it has NOT yet been classified.

**[OPEN CURRENT ONE-CELL READ-ONLY GitHub-versus-Notebook executable mapping reconciliation](notebooks/source-one-168-mapping-git-semantic-diff-readonly.py).**

Copy the **entire Python file** from GitHub and paste into **one NEW Python
cell** in the SAME successful SSP notebook session; execute that cell only.
No code downloads, no source reload, no Cells 1-7 rerun, no target SQL or
DIM/FACT COMMIT.

The executable does **not contain the private CSV**; it contains only
GitHub-derived SHA256 row digests for the 168 accepted records. It separately
checks the cached mapping inputs, the current Notebook Files CSV bytes and
their **18 executable columns** against the authoritative GitHub version
(blob `b9f982c445f293f9b5d47cab565194aa29ef8770`). Only
`NOTES` and CSV ordering/formatting are excluded from its semantic comparison.
It reports names of any differing mapped fields, never confidential Archer
values or Content IDs.

**Return:** `CACHED_EXECUTABLE_RULES_MATCH_GIT`,
`NOTEBOOK_FILE_EXECUTABLE_RULES_MATCH_GIT`,
`NOTEBOOK_FILE_EXACT_GIT_BLOB_MATCH`, `CACHED_RULES_MATCH_NOTEBOOK_FILE`
and `RESULT`. If it reports mismatches, return the short
`DIFFERING_FIELDS_MAX_20` lines too. Do **not** COMMIT.

**Validation:** Public script read back from GitHub, private test mirror
byte-identical; 7/7 focused CI tests PASS, including exact canonical Git CSV,
notes-only change, CSV order/line endings, changed transform and stale cached
file. Full suite retains baseline 28 FAIL/88 ERROR with zero new failures.
[Accepted QA and current checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-15-ssp-seven-object-live-value-fact-qa-pass-notebook-csv-drift.md).

---

## Earlier — seven-object PREVIEW value/FACT QA (accepted October 15, 2026)

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
