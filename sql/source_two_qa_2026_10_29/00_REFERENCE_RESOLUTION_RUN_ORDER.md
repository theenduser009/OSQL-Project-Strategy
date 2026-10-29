# Source Two — Archer reference resolution: SQL run order

**Prepared:** 2026-10-29. **Repository:** `theenduser009/OSQL-Project-Strategy`, public `main`. All tests are read-only Snowflake DEV SELECTs. **No live Snowflake execution by ChatGPT.**

The goal is to resolve `{ContentId, LevelId}` to the *specific Archer record and its business attributes* and then separately verify the associated OSCAL relationship. Do not treat a shared OSCAL property name, a preserved JSON array, or a target Content ID match as proof of full mapping.

## October 29 — SQL23 Policy Level 3 direct Sub-Section readback: passed

**New owner-executed Snowflake screenshots (October 29, 2026)** from
[SQL 23](23_POLICY_LEVEL3_DIRECT_SCALAR_AND_STRUCTURED_REFERENCE_QA.sql):
- Sub-Section direct `POLICY_LEVEL_3` has **2,349 INTEGER items**, across
  **818** owner records and **131** distinct candidate Content IDs. All **2,349**
  are positive numeric identifiers, match a UNIQUE
  `ARCHER_CONTENT_POLICIES_POLICY_LEVEL_3_RAW.CONTENT_ID`, and show no
  unmatched/duplicate-target/missing-target-CURATED_JSON occurrences.
- Combining direct numeric Sub-Section items with Source/Topic/Section inherited
  `{ContentId,LevelId=5}` objects yields **13,278/13,278** unique Level 3
  RAW target matches and **13,278** matched occurrences with nonblank policy
  names; **0** unsupported shapes, unmatched IDs, ambiguous target IDs or
  missing target JSON across the reported rows. **131 distinct referenced
  Policy Level 3 IDs** in total.
- The Sub-Section source items have no `LevelId` member. The target is
  established by the exact unique Level 3 RAW lookup, **not** by pretending
  those source items carried `LevelId=5`. Preserve that distinction.
- SQL 23 Query 3 owner screenshot returned sampled names/numbers for
  Sub-Section Content IDs. This verifies Archer source-to-policy business-value
  resolution, **not** OSCAL semantic links or completed end-to-end mapping.

**DO NOT rerun SQL22 or SQL23 for the same DEV snapshot.**
**NEXT:** [SQL 11 — field-scoped Source/Topic Component Definition property QA](11_SAME_FIELD_COMPONENT_POLICY_LEVEL.sql),
then inspect the actual OSCAL source/target value parity and distinguish the
direct `POLICY_LEVEL_3` field from derived descendant reference arrays.
Existing Source/Topic Component Definition commits were owner readback verified
October 28, but Section/Sub-Section Component Definition commits were not
established; do not misreport a missing property there as a failed committed route.

## Latest owner Snowflake evidence — Policy Level 3 (October 29)

**Policy Level 3 lookup is now proven in the owner-run snapshot.**
- `ARCHER_META_LEVEL.LEVEL_ID=5` resolves to Policy Level 3, module `POLICIES` (65).
- The matching physical policy table is `RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_POLICIES_POLICY_LEVEL_3_RAW`. Level 1 and Level 2 tables are not interchangeable for these LevelId=5 references.
- SQL22 Query 2 returned **13,278** reference occurrences: **10,929** valid structured LevelId=5 objects matched to `ARCHER_META_CONTENT` with **0 unmatched**, and **2,349** Sub-Section `POLICY_LEVEL_3` array items marked invalid by the *object-only* predicate. This is a shape limitation, not yet evidence those 2,349 are broken policy IDs.
- SQL22 Query 4 returned actual Policy Level 3 business names/numbers for the inspected matching policy records. This establishes Archer RAW business-value resolution for the sampled objects, **not** the native OSCAL semantic relationship.
- **Current next run: [SQL23](23_POLICY_LEVEL3_DIRECT_SCALAR_AND_STRUCTURED_REFERENCE_QA.sql), Query 01 then 02.** It profiles the direct Sub-Section array and tests numeric candidates against the exact L3 `_RAW` table. Its third query displays sampled source-to-policy names. If source-to-record coverage passes, continue to [SQL11](11_SAME_FIELD_COMPONENT_POLICY_LEVEL.sql) for field-specific persisted Component Definition prop attribution.
- The earlier Control Procedures LevelId=39 coverage SQL is a different scope; it should not be rerun to solve Policy Level 3.

## October 29 — Policy Level 1/2/3 RAW-only table discovery

The policy-table searches in
[SQL 22](22_POLICY_LEVEL3_REFERENCE_COVERAGE_AND_RECORD_LOOKUP.sql),
[SQL 19](19_ARCHER_CONTENTID_LEVELID_METADATA_RECORD_LOOKUP.sql), and
[SQL 16](16_POLICY_LEVEL5_META_AND_RECORD_RESOLVER.sql)
were narrowed to tables with names conforming to
`ARCHER_CONTENT_POLICIES_(POLICY_)?LEVEL_[123]_RAW`.
They now exclude `_STG`, `_TMP`, `_BASE`, and other similarly named
objects. Owner's October 29 Snowflake screenshot later established the
exact Level 3 table as `RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_POLICIES_POLICY_LEVEL_3_RAW`.

**Historical run order (already executed in owner snapshots):** SQL22 Query 2, 3, 4.
They established structured reference matches, the exact Level 3 RAW table and
sampled business names; these do **not** prove a native OSCAL semantic relationship.

## Begin here

1. **[SQL 20 — confirm Level IDs and Control Procedures references](20_LEVEL5_LEVEL39_CONTROL_PROCEDURE_REFERENCE_QA.sql)** — Four runnable, standalone SELECTs. Run Query 01 first to check actual `ARCHER_META_LEVEL` metadata for Level IDs `5` and `39`. Run Query 02 for **`RELATED_CONTROL_PROCEDURES` across Source, Topic, Section, Sub-Section** versus the verified physical table name `ARCHER_CONTENT_CONTROL_PROCEDURES_RAW`. It reports invalid IDs, wrong levels, missing targets, duplicates and missing curated JSON. Run Query 03 for **per-origin Content ID lineage**, then Query 04 for candidate populated target business fields.
2. **[SQL 19 — ContentId → Meta Content → level/module metadata](19_ARCHER_CONTENTID_LEVELID_METADATA_RECORD_LOOKUP.sql)** — Five SELECTs. It uses the historically observed `ARCHER_META_CONTENT.CONTENT_ID` and discovers actual Meta Content/Level/Module field names. It also extracts policy `ContentId/LevelId` references from OSCAL Component Definition. **Replace the explicit placeholders** with the relevant real IDs in your own authorized Snowsight worksheet.
3. **[SQL 15 — parse preserved OSCAL policy-reference arrays](15_CATALOG_COMPONENT_POLICY_CONTENTID_LEVELID_PARSE_DIAGNOSTIC.sql)** — See which stored values are structured reference objects versus non-reference scalar properties.
4. **[SQL 18 — Matillion enrichment and job-history diagnostics](18_MATILLION_ENRICHMENT_AND_NUMERIC_POLICY_REFERENCE_DIAGNOSTIC.sql)** — Tests enrichment evidence and optional accessible UPDATE query history. Query 01 requires the actual physical policy table name. **The owner previously ran an older `RESULT_SCAN` version**; copy the latest GitHub file. Query 04A is limited by query-history visibility; 04B is optional Account Usage.
5. **[SQL 03 — DIM-only Component Definition field attribution](dim_fact_only_2026_10_29/03_COMPONENT_DEFINITION_TWO.sql)** — Independent target-value attribution by source table/record and field identity, not a reference-record hydration test.

## Data contract and limitations

- `LevelId` in structured record references identifies an Archer application level; `ContentId` identifies a referenced record. `ARCHER_META_VALUE` handles select-list IDs rather than these record links.
- **Source Two policy LevelId 5** is supported by October 26 Policy Level 2 reference samples, but its actual `ARCHER_META_LEVEL` row is not yet owner-run verified in this chat. **LevelId 39** is tested by Codex's Control Procedures SQL; its metadata label also requires actual query output.
- `ARCHER_META_CONTENT` was observed in the September 10, 2026 owner Snowflake source lookup with unique `CONTENT_ID` keys; actual owning LevelId column and module joins must be confirmed by SQL19.
- **Codex screenshot-derived SQL** checked `RELATED_CONTROL_PROCEDURES` across four levels against `ARCHER_CONTENT_CONTROL_PROCEDURES_RAW`. SQL20 is a reconstructed, clearer implementation with owner Content IDs in Query03. It is **not** claimed byte-for-byte identical to Codex's hidden original code.
- **Earlier 39,897 matched Control Standard references (October 9)** are not the same as Control Procedures. Do not reuse that acceptance for SQL20.
- Even a perfect match on `ARCHER_CONTENT_CONTROL_PROCEDURES_RAW.CONTENT_ID` does **not** prove that its name/title was enriched or that an OSCAL native relationship was written. Query04 discovers candidate business fields but does not choose an unapproved name.
- The current Matillion candidate converts numeric **Field IDs** via `ARCHER_META_FIELD`, and enriches User/ValueList/Group IDs. It does not currently hydrate cross-application `ContentId/LevelId` policy/procedure records.
- October 27 Source Two Catalog/AR/SAP owner-reported COMMIT and October 28 Component Definition Source/Topic owner-reported COMMIT remain accepted within their observed route scope. These reference QA SELECTs do not authorize or require another COMMIT.

## What to record from the run

For Query 1, note the actual LevelID 5/39 names. For Query 2, capture counts by `SOURCE_LEVEL` and `ALL` including `INVALID_LEVEL39_REFS`, `UNMATCHED_OCCURRENCES`, `OCCURRENCES_WITH_DUPLICATE_RAW_TARGET_IDS`, and `OCCURRENCES_WITH_TARGET_JSON_MISSING`. For Query 3, inspect source-level/owner Content ID and reference status. Keep actual business payloads outside public GitHub.

**Publication validation:** Source SHA/branches inspected, public files created and read back byte-for-byte; no Snowflake compilation, database readback or mapping changes performed.
