# Source Two — Archer reference resolution: SQL run order

**Prepared:** 2026-10-29. **Repository:** `theenduser009/OSQL-Project-Strategy`, public `main`. All tests are read-only Snowflake DEV SELECTs. **No live Snowflake execution by ChatGPT.**

The goal is to resolve `{ContentId, LevelId}` to the *specific Archer record and its business attributes* and then separately verify the associated OSCAL relationship. Do not treat a shared OSCAL property name, a preserved JSON array, or a target Content ID match as proof of full mapping.

## October 29 — Policy Level 1/2/3 RAW-only table discovery

The policy-table searches in
[SQL 22](22_POLICY_LEVEL3_REFERENCE_COVERAGE_AND_RECORD_LOOKUP.sql),
[SQL 19](19_ARCHER_CONTENTID_LEVELID_METADATA_RECORD_LOOKUP.sql), and
[SQL 16](16_POLICY_LEVEL5_META_AND_RECORD_RESOLVER.sql)
were narrowed to tables with names conforming to
`ARCHER_CONTENT_POLICIES_(POLICY_)?LEVEL_[123]_RAW`.
They now exclude `_STG`, `_TMP`, `_BASE`, and other similarly named
objects; the exact live physical Level 3 table name still must be confirmed
from Query 3 output before running SQL22 Query 4.

**Next:** If Query 2's reference coverage is clean and Query 3 identifies the
real Level 3 RAW table, run Query 4 for source-owner -> referenced policy record
-> policy name/number/purpose. A matched record does **not** prove the OSCAL
semantic relationship has been implemented.

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
