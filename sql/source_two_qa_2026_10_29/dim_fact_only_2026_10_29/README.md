# OSCAL QA — DIM/FACT only — two queries per model or section

**Date:** October 29, 2026  
**Source inspection:** private `theenduser009/Oscal-mapping-strategy` `simplify-metadata-boundary` at `9398f6de6b78b5f0c2c183bd01d960f0f37ab827`; relevant exact mapping CSV, registry setup and source helper code.  
**Live database validation:** NOT RUN. Current deployed notebook SHA and live registry contents NOT independently verified. No database writes.

## Start here

Copy one standalone `SELECT` at a time into Snowflake DEV. Each example has exactly:

```
CONTENT_ID | SOURCE_TABLE_NAME | OSCAL_ELEMENT_PATH |
OSCAL_ELEMENT | ARCHER_FIELD_NAME | FIELD_VALUE
```

No query reads `_RAW` tables or the Archer source JSON. `SOURCE_TABLE_NAME`
is retained provenance in a DIM record (or for embedded Catalog children, the
child level inferred from FACT ancestry). `FIELD_VALUE` is the **stored OSCAL**
value, not a proof that original Archer values were equal.

| Artifact / section | Two queries | Field identity rule |
|---|---|---|
| Catalog — Metadata | [01 Catalog Metadata](01_CATALOG_METADATA_TWO.sql) | Source-level `SOURCE_NAME` → metadata.title, `SOURCE_VERSION` → metadata.version; both are mapping-defined native member names |
| Catalog — Group hierarchy | [02 Catalog Groups](02_CATALOG_GROUP_TWO.sql) | Topic/Section `NUMBER_OF_CONTROL_STANDARDS_*_LEVEL` → `control-count`; original child Content ID in `archer-content-id`, FACT ancestry separates levels |
| Component Definition | [03 Component Definition](03_COMPONENT_DEFINITION_TWO.sql) | `POLICY_LEVEL_3` vs `POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS`, both `policy-level`; field-and-value derived DIM hash distinguishes them |
| Assessment Results | [04 Assessment Results](04_ASSESSMENT_RESULTS_TWO.sql) | `COMPLIANCE_RATING` in Topic and Section; same property name but separately stored source-table/record/field identities |
| Assessment Plan | [05 Assessment Plan](05_ASSESSMENT_PLAN_TWO.sql) | **Source One** `REQUEST_TO_BEGIN_ASSESSMENT` and `APPROVAL_TO_BEGIN_ASSESSMENT` with exact `SOURCE_FIELD_NAME` identity. Source Two SAP was committed separately October 27, but its **deployed field-level mapping was not verified** in the checked-in contract, so do not relabel Source One examples as Source Two |
| System Security Plan | [06 SSP](06_SSP_TWO.sql) | **Source One** `AUTHORIZATION_PACKAGE_NAME` → system-name and metadata.title; two approved native members |
| POA&M | [07 POAM](07_POAM_TWO.sql) | **Source One** `POAMS` → poam-items; first returns item payload, second FACT target UUID. These are **OSCAL target values**, not reconstructable original Archer reference IDs |
| Catalog — Back Matter | [08 Back Matter discovery](08_CATALOG_BACK_MATTER_DISCOVERY_TWO.sql) | **Not a verified native mapping.** Two target-only exploratory scans for resource rlinks and base64; labels marked `UNVERIFIED`. No source-field attribution or test PASS may be inferred |

## Why simply showing the name is insufficient

OSCAL DIM has `SOURCE_TABLE_NAME`, `SOURCE_RECORD_ID`, `ELEMENT_TYPE`,
`METADATA_JSON`, hashes and UUIDs, but no universal `ARCHER_FIELD_NAME` column
and no universal `ELEMENT_PATH` column. Exact Archer field names in these
queries are either **pinned from the approved mapping** (native members) or
**reconstructed from field-aware deterministic identity** (separately stored
properties). Catalog hierarchy has embedded child Content IDs, while its
warehouse `SOURCE_RECORD_ID` can refer to the root Source. Field names cannot
be universally recovered from arbitrary OSCAL values without provenance.

**Do not use these two-field examples as whole-model certification.** A missing
value can mean the source field was missing/null, the mapping omitted it,
a route was not committed, the live snapshot differs, or the active identity
rule differs. The examples do not independently verify original Archer values;
your separate RAW-side tester performs that comparison. For an accurate PASS,
confirm deployed registry, mappings, transform and its Source-to-Target equality.

## Dated evidence precedence

- October 27, 2026: owner-supplied eight-route `COMMITTED_AND_VERIFIED` evidence
  for Source Two Catalog, AR and SAP (model and scope as recorded).
- October 28, 2026: owner-supplied `COMMITTED_AND_VERIFIED` evidence **only for**
  Source and Topic Component Definition. Not Section/Sub-Section Component Definition.
- October 28, 2026: separate Catalog Source +1,502 DIM/+1,502 FACT is only a
  **PREVIEW**, not proven committed by those receipts.
- No live Snowflake query was performed while publishing this collection.
