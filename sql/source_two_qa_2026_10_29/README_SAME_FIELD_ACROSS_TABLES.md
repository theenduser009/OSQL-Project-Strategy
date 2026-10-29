# Source Two — same Archer field across different tables: QA demo

**Prepared:** 2026-10-29. **Environment:** Snowflake DEV, read-only. **Target:** seven-column tester output.

The same field name and OSCAL property path do **not** identify the source. The
meaningful identity is the **OSCAL model + exact Archer SOURCE_TABLE_NAME +
SOURCE_RECORD_ID (Archer CONTENT_ID) + source field + field-specific property
identity/parent relationship**. Do not join only by property name, or by Content
ID without the source table. This previously made a null `POLICY_LEVEL_3`
appear to own a populated `policy-level` value.

## Copy and run one SQL file at a time

1. [11 — Component Definition: POLlCY_LEVEL_3 and derived field names across Source and Topic](11_SAME_FIELD_COMPONENT_POLICY_LEVEL.sql). Reconstructs the **field-and-value DIM hash** so two fields writing the same `policy-level` name are separated. The Source and Topic routes were **owner-reported COMMITTED_AND_VERIFIED on 2026-10-28**. A null source with a populated field-owned target needs stale snapshot/transform investigation, not an assumed pass.
2. [12 — Assessment Results: COMPLIANCE_RATING across Source, Topic, Section and Sub-Section](12_SAME_FIELD_ASSESSMENT_RESULTS_COMPLIANCE.sql). Uses the **exact source-table-scoped field identity hash**. Owner's 2026-10-27 eight-route receipt verifies AR **Topic/Section/Sub-Section**; it does not establish Source/AR commit.
3. [13 — Catalog: RELATED_TO_KEY_CONTROLS across Topic, Section and Sub-Section](13_SAME_FIELD_CATALOG_RELATED_CONTROLS.sql). Catalog child group rows are stored under the **Source-owned** document. The SQL uses each embedded `archer-content-id` and **FACT parent depth** to identify the real child table/record. Property-name match is **candidate** evidence, not proof of a unique source field when the compiled mapping contains collisions.

Every query emits exactly:

```
ARCHER_TABLE_NAME | CONTENT_ID | ARCHER_FIELD_NAME | ARCHER_VALUE |
OSCAL_PROPERTY_NAME | OSCAL_ELEMENT_TYPE | OSCAL_VALUE
```

The output shows a balanced **sample of up to eight source rows per table or field**;
remove/adjust the final `QUALIFY` to inspect more. A null OSCAL_VALUE can mean
absent source, omitted target, uncommitted route, or mismatching deployed identity
contract. **Do not award a mapping QA PASS from null/empty source evidence**.
If a populated source has an empty target, verify runtime fingerprint/registry
before classifying it as a real mapping defect.

**Evidence basis:** `theenduser009/Oscal-mapping-strategy` branch
`simplify-metadata-boundary` at `9398f6de6b78b5f0c2c183bd01d960f0f37ab827`,
current source code Cells 4–5, owner checkpoint 2026-10-27 for AR/Catalog/SAP,
and owner checkpoint 2026-10-28 for Component Definition Source/Topic.
No live Snowflake execution, current deployed notebook SHA, or every individual
field-value match was independently verified while publishing these SQL files.
No actual Archer payloads or customer values are included in Git.
