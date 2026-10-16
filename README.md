# OSCAL — public copy-and-run workbench

## CURRENT — Oct 16, 2026: Source Two 75-row CATALOG QA PASS; guarded 30,566 DIM COMMIT next

**Owner-run read-only QA just passed in Snowflake DEV.** Of FIVE new
CATALOG field mappings, **Section `TOPIC_NAME` 10,566/10,566** and
**Sub-Section `TOPIC_NAME` 20,000/20,000** matched their exact
embedded group `props[topic]`; **zero mismatches**, exact changed
path gate PASS, 62 CATALOG mapping rules, mapping fingerprint matches
the current 30,566-update PREVIEW. The THREE other Source/Section
Content ID/confirmation fields have **0 populated original source
values** and were correctly omitted—not tested with populated values.
The `result` is `PASS_VALUES_AND_PATHS_SOURCE_EMPTY_FIELDS_UNTESTED`,
not a five-populated-field PASS. No target DML/COMMIT yet.
The previous separate CATALOG 31,982-DIM-update release was already
COMMITTED_AND_VERIFIED, must not be rerun.

**ONE NEXT OWNER ACTION**
[OPEN AND COPY COMPLETE CATALOG 30,566-UPDATE COMMIT APPROVAL GUARD
(one read-only Python cell)](notebooks/source-two-catalog-30566-commit-approval-guard.py).
Paste into ONE NEW Python cell in the same existing
`NB_ARCHER_OSCAL_MAPPER_V2` Snowflake DEV session.
Run the guard only and require
`CATALOG_DEV_COMMIT_GUARD_ARMED_NO_WRITES`.
It verifies the exact PREVIEW/QA/fingerprint and arms the optional
existing Cell6 exact change/retirement envelope; the guard itself
**does not write to Snowflake**.

**THEN** the owner explicitly changes **existing Cell 7 only** to
`OSCAL_LOAD_MODE="COMMIT"` and runs that cell **ONCE** with no
concurrent Catalog target writer. Do not rerun Cells1–6.
Expected guard values: DIM 0 inserts/30,566 updates/3,113 unchanged;
FACT 0 inserts/0 updates/33,531 unchanged; zero retirements.
Only accept `COMMITTED_AND_VERIFIED` with zero pending inserts/updates
in the nested post-COMMIT readback. Unknown outcome = STOP, no retry.
Return full new `OSCAL_PIPELINE_REPORT`.

Public executable and private
`Oscal-mapping-strategy/simplify-metadata-boundary/notebooks/validation/READ_ONLY_CATALOG_30566_EXACT_COMMIT_APPROVAL_GUARD_2026_10_16.py`
byte-identical Git blob
`11770903b309f288bbf5c251b7c377a8d0b5b66d`,
actual GitHub re-fetch verified. Static no-SQL/write and scope checks
passed; guard not yet run in Snowflake, and commit not yet performed.

[Authoritative private QA/guard checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-75row-five-new-field-live-qa-pass-empty-source-30566-guarded-commit-next.md).
CATALOG ONLY across four Source Two tables until fully dispositioned.
Native controls and Back Matter remain unresolved; prior October 13
Control Standards ID/title profiler already run—do not repeat.
Older “current” sections below are historical.

---


## CURRENT — October 16, 2026: Source Two CATALOG 75-row PREVIEW PASS (30,566 updates); five new-field QA next

Owner Snowflake DEV `NB_ARCHER_OSCAL_MAPPER_V2` now reports
`source-two-source / CATALOG`, **`PREVIEW_COMPLETE / PREVIEW_PASSED_NO_TARGET_DML`**:
148 source records, 33,679 DIM, 33,531 FACT, **30,566 proposed DIM updates**
and 3,113 unchanged, 0 new inserts or FACT changes, 0 lineage gaps,
valid graph/storage/prewrite contract, 0 retirements, no writes or COMMIT.
This supersedes the old **75-row PREVIEW pending** task below.
The earlier **31,982-DIM-update CATALOG COMMITTED_AND_VERIFIED** remains
a separate completed prior batch—never repeat it.

**ONE NEXT ACTION — [OPEN/COPY THE COMPLETE 75-ROW CATALOG FIVE-NEW-FIELD
READ-ONLY QA PYTHON FILE](notebooks/source-two-catalog-next-five-30566-preview-value-qa-readonly.py).**
Paste its full contents into ONE NEW Python cell in the SAME
successful Snowflake DEV notebook; run ONLY that cell. It reuses
the current retained `MODEL_GRAPHS`, `PIPELINE_REPORT`,
`SOURCE_INPUTS`, validates 62 selected CATALOG rules and
the 30,566-update envelope and exact field paths, compares all
five new Source/Section/Sub-Section fields to their original
cached Archer values and checks changed DIM paths from read-only
Snowpark SELECTs. It prints per-field counts, including
populated vs absent source data, **no raw record IDs/values**.
Return `SOURCE_TWO_NEXT_FIVE_QA` and the final `result`.
**No rerun Cells 1–7, no COMMIT, no target DML.**

The public file matches the PRIVATE mirrored validation cell at
`Oscal-mapping-strategy/simplify-metadata-boundary/notebooks/validation/READ_ONLY_SOURCE_TWO_CATALOG_75_ROW_NEXT_FIVE_30566_PREVIEW_QA_2026_10_16.py`,
both readback-verified exact Git blob
`996dfa270acbc077a30f6ba7fa3302907d0fbca9`.
Static no-write and field-scope checks completed.
**This new QA cell has not yet been executed in live Snowflake
or independently Python syntax/runtime-tested.**

[Latest source-of-truth private checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-75-row-preview-30566-updates-next-five-readonly-parity.md).
All four Source Two tables remain scoped to **CATALOG only**;
no Assessment Results or Component Definition model switch.
Older workbook/Control Standards deferral decisions are preserved
in the private project continuity documents.

---

## CURRENT — Oct 16: Source Two CATALOG next five scalar PREVIEW-only input prepared

**The previous 31,982 Source Two Catalog DIM updates are physically
COMMITTED_AND_VERIFIED**, with 0 FACT changes and loader
postcommit 0 pending rows. Do not rerun Cell7 COMMIT or old QA.

A NEW five-field Catalog-only incremental file has been staged
**PRIVATELY**, not published here because the full source mapping CSV
is private. [Open exact private GitHub file and instructions](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/release_candidates/2026-10-16-catalog-next-five-preview-only/README.md).
Private file `Mapping/release_candidates/2026-10-16-catalog-next-five-preview-only/sources_source_runtime.csv`
has 75 mapping rows / 62 selected CATALOG rules and preserves
previous 70-row reviewed candidate exact. Newly appended fields
include Source content id and confirmed-date, Section topic-name/
confirmed-date, Sub-Section topic-name props, all using existing
seven-cell mapper transforms.

**ONE next user action, NOT a COMMIT:** In existing Snowflake DEV
`NB_ARCHER_OSCAL_MAPPER_V2`, replace ONLY Notebook Files
`sources_source_runtime.csv` with this private 75-row version,
select `CATALOG` only, keep shared writes FALSE, set Cell7
`OSCAL_LOAD_MODE="PREVIEW"`, run Cells1→7 once and return one
`OSCAL_PIPELINE_REPORT`. No new parser/registry needed; do not
assume prospective DIM updates. Batch source-value QA follows preview.

**Do not run the public `source-two-control-standards-populated-id-title-readonly.py`
again.** The owner ALREADY ran this business ID/title work October 13;
the older October 9 profiler-pending notes below are superseded.
1,606 referenced Control Standards code-like names are present,
1,603 requirements, 919 authoritative alternative IDs/descriptive titles,
844 alternate ARCHER IDs/names, 687 missing both; owner previously
chose to DEFER native controls pending title/reuse policy. Direct
39,897/39,897 Control Standards reference matches also already accepted.
Preserve these, native controls and Back Matter remain CATALOG scope.
**Do not jump to Assessment Results or Component Definition.**

[New private dated Catalog-first checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-next-five-75-row-preview-release-ready.md).

---

## CURRENT — October 16: Source Two CATALOG first; five-field COMMIT completed, next five scalars staged

**Owner Snowflake DEV actual:** latest `source-two-source / CATALOG`
**COMMITTED_AND_VERIFIED** with 148 roots, 33,679 DIM and
33,531 FACT, **31,982 DIM updates**, 0 FACT changes and zero
pending post-COMMIT inserts/updates. Earlier five-field source-value
QA matched 53,398/53,398. **Do not rerun COMMIT or old QA.**

**Owner scope decision:** complete all CATALOG mappings across four
Source Two worksheets (Source, Topic, Section, Sub-Section)—including
Catalog Metadata, Group, native controls/Back Matter dispositions—
**before** moving to Assessment Results/Component Definition.

**Actual private Source Two XLSX and its 243 mapping rows were checked.**
[Private four-level mapping disposition](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/SOURCE2_CATALOG_FOUR_TAB_FULL_FIELD_DISPOSITION_2026-10-16.csv)
has 57 selected Catalog rules, 107 unrelated-model worksheet rows for
later, 79 Catalog-related/derived/native/control/Back Matter review rows.
A new 75-row private [five-more-field Catalog proposal](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/release_candidates/2026-10-16-catalog-profile-next/REVIEW_ONLY_75_ROW_NEXT_FIVE_CATALOG_SCALAR_CANDIDATE.csv)
is STAGED REVIEW ONLY. It preserves the previous 70 rows, adds five
straightforward Source/Section/Sub-Section props using the existing
generic engine, and has not been owner-approved, PREVIEWED or COMMITTED.

**IMPORTANT newer owner history:** Prior October 13 Control Standards
business-field analysis was ALREADY EXECUTED (1,606 distinct referenced
Control Standards, code-like `CONTROL_STANDARD_NAME` present in all,
but 687 without both alternate business IDs/descriptive titles).
The owner explicitly DEFERRED native controls[] until authoritative
title/reuse handling was chosen. The October 9 ID/title diagnostic
[`notebooks/source-two-control-standards-populated-id-title-readonly.py`](notebooks/source-two-control-standards-populated-id-title-readonly.py)
was republished as a historical utility, **NOT a CURRENT action**.
**DO NOT run it again** or repeat the already accepted 39,897/39,897
direct `CONTROL_STANDARDS` target-ID reconciliation.

**One next owner action:** review/approve the FIVE exact Source2 Catalog
scalar property mappings in the private 75-row candidate as a single
batch; then a new CATALOG-only DEV PREVIEW and field-value QA,
separate later COMMIT on authorization. Native Control Standards
and Back Matter remain Catalog-only work requiring explicit scope/
title/URI decisions, not automatic new IDs or model hopping.

[Authoritative dated private checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-243-row-reconciliation-and-next-five-scalars.md).
All older "current" sections below are retained as dated history and
superseded by this status. Public repo holds sanitized copy-run
diagnostics, never confidential mapping CSVs, payloads or credentials.

---


## CURRENT — October 16: CATALOG 31,982-update PREVIEW PASS; FIVE-FIELD QA before COMMIT

**New owner Snowflake DEV screenshot:** one `source-two-source / CATALOG`
`PREVIEW_COMPLETE`, 148 roots, 33,679 candidate DIM, 33,531 FACT,
**31,982 proposed DIM updates**, 1,697 unchanged DIM, 0 DIM/FACT
inserts and 0 FACT changes, no lineage gaps, graph/storage/prewrite
PASS, **zero writes/persisted/committed**. This is the next five-field
batch **PREVIEW only**. The older 11,982-DIM-update CATALOG
`COMMITTED_AND_VERIFIED` is an older accepted batch and **must not
be rerun**.

**ONE NEXT ACTION — COPY AND RUN [COMPLETE FIVE-FIELD CATALOG PREVIEW
PARITY READ-ONLY PYTHON FILE](notebooks/source-two-catalog-five-field-preview-parity-readonly.py).**

Open the GitHub file, copy its entire contents into ONE NEW Python
cell in the SAME `NB_ARCHER_OSCAL_MAPPER_V2` DEV notebook after the
successful 31,982-update PREVIEW, and execute **only that cell**.
Do **NOT** change Cell 7 to COMMIT or rerun Cells 1–7.

The single cell verifies all FIVE mapped Archer child fields against
their exact CATALOG group-property values, uses the real Source Two
child identity/parent hierarchy, and runs READ-ONLY Snowpark SELECTs
to ensure changed DIM paths are **only** 1,416 Topic, 10,566 Section,
20,000 Sub-Section. It also verifies the selected 57 CATALOG rules,
mapping fingerprint and exact 31,982-update PREVIEW envelope.
The code prints only aggregate field counts/path counts—not Archer
business values or Content IDs. No DDL, DML, MERGE, COMMIT, registry
mutation, or new source load.

**Return** `OSCAL_FIVE_FIELD_QA_REPORT` including
`result`, `field_mismatches_total`, `changed_path_gate`,
`updated_path_counts` and `missing_dim_target_keys`.
If the QA blocks, do NOT COMMIT—return its report.
Even if it passes, physical COMMIT remains a separate owner
decision; the Section property name `sub-section-criticality-sum`
is a proposed extension property whose original source worksheet
suffix was clipped.

**GitHub publication verified:** public file and private
`Oscal-mapping-strategy/simplify-metadata-boundary/notebooks/validation/READ_ONLY_SOURCE_TWO_CATALOG_FIVE_FIELD_PREVIEW_PARITY_2026_10_16.py`
have identical Git blob `ec06c6fea5aabf2905b4f4a33e86d5f62256064b`.
Static no-write/scope checks and GitHub readback pass;
**Snowflake live QA is pending**.
[Latest private dated checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-31982-preview-five-field-parity-next-no-commit.md)
(requires authenticated private GitHub access).

---


## CURRENT — Oct 16: five Source Two Catalog property mappings drafted; do not rerun completed work

The owner's most recent two Snowflake screenshots are a repeat of the
**completed FIRST 11-field read-only profile** `READ_ONLY_SOURCE_TWO_CATALOG_FIELD_SHAPES`.
They do not show execution of the second detailed link/number profiler.
**A second broad profile is NOT required to decide the next five straightforward
Catalog group property mappings.** The previous CATALOG
`COMMITTED_AND_VERIFIED` with **11,982 DIM updates** and **0 FACT updates**
remains accepted; do not rerun that commit.

The private OSCAL repository `simplify-metadata-boundary` now has a
**REVIEW-ONLY 70-row mapping candidate** derived from the current 67-row
candidate. It maps four Topic/Sub-Section creation/update timestamps to
named group extension properties (without inventing timezone) and one
Section sub-section criticality sum numeric property. It has **NOT**
been owner-approved, copied into Snowflake Notebook Files, previewed or
committed. No production seven-cell code, active mappings or registry
was changed. The Section sum property name remains a proposal because
the source worksheet transcription is clipped.

[Private 70-row candidate and five-field mapping details](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-70-row-five-field-staged-metadata-only-no-deployment.md)
(requires authenticated private GitHub access).

**NEXT ACTION:** approve/correct the five specific proposed
field/property destinations, especially `sub-section-criticality-sum`.
Then the private executable Source Two release can be prepared and
tested, followed by ONE CATALOG `PREVIEW` and field-level source/target
QA before any separately approved COMMIT. **No new Snowflake cell needs
running now for these five decisions.**

The existing [optional second targeted Source-links and strict
date/number diagnostic](notebooks/source-two-catalog-links-and-scalar-gates-readonly.py)
remains available **only for the later native `SOURCE_LINKS` / source
timestamp semantics investigation**, not as a gate blocking these five.
No private CSV or client information is in this public README.

---


## CURRENT — Source Two 11-field live profile reviewed; next exact shape check (2026-10-16)

**Owner live Snowflake DEV evidence:** Existing PUBLIC 11-field
read-only profiler was executed in the SAME seven-cell Snowflake
notebook. Source `SOURCE_LINKS` = 62 nonempty object arrays /
86 nulls (148 records); all 148 Source, 1,416 Topic and
20,000 Sub-Section date/create/updated fields are **timestamp-shaped
strings with no timezone offset**; Section criticality sum is
10,566 numeric values; Section `INFORMATION` and Sub-Section
`INFORMATION`/`SUBSECTION_CRITICALITY_VALUE` have no populated values.
This is **source shape profiling**, not a new mapping/warehouse COMMIT.

The earlier completed CATALOG `COMMITTED_AND_VERIFIED` state remains
accepted: **11,982 DIM updates**, zero FACT changes, 148 records,
33,679 DIM nodes and 33,531 FACT edges; post-COMMIT loader readback
had 0 remaining changes. **Do not rerun this COMMIT.**

**ONE NEXT ACTION — [OPEN THE COMPLETE PUBLIC ONE-CELL Source Two LINKS + SCALAR DETAIL QA](notebooks/source-two-catalog-links-and-scalar-gates-readonly.py)**

Copy the entire linked Python file into ONE NEW Python cell in the
same `NB_ARCHER_OSCAL_MAPPER_V2` Snowflake DEV session and run **only
that cell**. It reuses the retained four-level source snapshot and
prints only aggregate `source_links` member/key/type/URI-scheme
counts, strict timestamp validity/timezone/whitespace counts for six
date fields, and finite numeric counts for Section criticality.
**It does not print URLs/business values/Content IDs or modify
DIM, FACT or registry; no DDL, DML, MERGE or COMMIT.**
Return JSON status `READ_ONLY_SOURCE_TWO_NEXT_MAPPING_DETAIL_GATES`.

[Private latest owner source-profile checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-eleven-field-owner-live-profiler-and-next-map-gates.md)
and [next five-group-prop proposal / detailed QA checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-catalog-next-five-group-props-proposed-public-detail-qa.md)
require owner-authorized private access. Public/private diagnostic
mirrors are identical Git blob
`a0d294f90500a9d75e85f2e8b6539c55ee6ea0ef`;
a non-executable private 11-field candidate review ledger exists,
but **no executable Source Two CSV, seven production cells, registry
or Snowflake target data was changed** by this new mapping review.
Public/private GitHub readback and no-write static checks passed;
the detailed QA has **not yet been live executed in Snowflake**.

---


## CURRENT — Source Two CATALOG COMMITTED; next field profiler ready (2026-10-16)

**Owner Snowflake DEV COMMIT verified:** Existing single seven-cell
`NB_ARCHER_OSCAL_MAPPER_V2`, `source-two-source / CATALOG`, now reports
`COMMITTED_AND_VERIFIED`: **148 records, 33,679 DIM, 33,531 FACT**;
**11,982 DIM updates**, **0 DIM/FACT inserts, 0 FACT updates**,
0 lineage gaps/approved retirements. Built-in post-COMMIT readback
found **0 pending DIM/FACT inserts or updates**. These are new
owner-supplied live results, superseding the earlier CATALOG
`PREVIEW pending` / `COMMIT pending` sections below.
**Do not run that COMMIT again.** This does not establish new
Assessment Results/POAM/SAP commits or full OSCAL document conformance.

**NEXT ACTION — OPEN AND COPY ONE READ-ONLY PYTHON CELL:**

[**Source Two CATALOG next-field profiler — open this complete Python file**](notebooks/source-two-catalog-next-fields-readonly.py)

1. Click the linked file in this public repository.
2. Copy its entire contents into **one NEW Python cell** in the
   **same** Snowflake DEV notebook `NB_ARCHER_OSCAL_MAPPER_V2`.
3. Execute **only that cell**. It reuses retained Source Two
   Source/Topic/Section/Sub-Section frames and prints field-wise
   `rows_scanned` and `shape_counts` for **11 field/level combinations**.
   Return the aggregate `READ_ONLY_SOURCE_TWO_CATALOG_FIELD_SHAPES` JSON.
   **Do not rerun Cells 1–7 or COMMIT.**

The profiler issues read-only Snowpark SELECT operations on retained
frames. It has **no target DIM/FACT writes, MERGE, registry DDL or COMMIT**.
It prints no business values or Content IDs. If retained frames are
missing, it stops; do not rebuild or repeat a completed COMMIT.

**Code and checkpoint boundaries:** All production seven-cell mapper
code, private mappings, status and owner-specific evidence remain in
the **private** `theenduser009/Oscal-mapping-strategy` repository,
branch `simplify-metadata-boundary`. Public `OSQL-Project-Strategy/main/notebooks/`
is **copy-and-run read-only diagnostics only**, not a second mapper.
See the private [canonical code/evidence directory guide](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/CODE_LOCATIONS_AND_EVIDENCE_PRECEDENCE.md)
and [October 16 COMMIT checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-source-two-catalog-11982-dim-updates-owner-commit-readback.md)
(authenticated private access required).

**Publication gate:** public executable and private mirror Git blob
`225f4aabbe1f86e7ce71ad11e3254c621a7f9a64`
match; exact-file Python syntax and mocked four-level, 11-field
aggregate-only tests PASS. This is **not a live Snowflake run of the profiler**.
The public file contains no private mapping CSV, source values or credentials.

---


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
