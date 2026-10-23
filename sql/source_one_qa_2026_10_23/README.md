# "Fields are not found.xlsx" — exact photographed field QA

**Evidence/scope date:** 2026-10-23. **Only the 25 identifiable Archer field names in the owner-supplied screenshot** are part of this pack. It is not a full Source One regression.

**Runtime mapping basis:** private OSCAL repository `theenduser009/Oscal-mapping-strategy`, branch `simplify-metadata-boundary` at `7c27ab51d8d95e8a39e799e55fffda41b4026542`. Mapping CSV `Mapping/ARCHER_OSCAL_MAPPINGS.csv`, blob `b9f982c445f293f9b5d47cab565194aa29ef8770`. Script creation/read-back is **not** Snowflake execution.

## Screenshot count and unclear row

- Rows numbered 1–17 and 19–25 each show an Archer field (24 named fields).
- The immediately following **unnumbered** row `BASELINE_RECOMMENDATION` is visibly a named field (one more).
- Row **18** appears shifted/malformed: "System Security Plan" is shown in the Archer-name column, followed by an OSCAL path and "Extension Property"; this is insufficient to identify an exact source key. It is an **unresolved owner worksheet row**, not an executable field.
- **Total executable/source-profiled field entries: 25** (23 APPROVED, 2 DEFERRED). `INFORMATION_CLASSIFICATION` and `DAILY_LOSS_AMOUNT_FROM_OUTAGE` were later follow-up requests, not rows in the original photographed screenshot, so they are intentionally excluded. The separate published QA SQL for them is retained outside this folder.

## Run the QA

Run these READ-ONLY Snowflake DEV SQL scripts and retain the full output privately. They are designed to separate `SOURCE_KEY_ABSENT` / `SOURCE_EMPTY` / explicit JSON null from populated-source missing target, matching value, mismatch or identity-only partial review.

| Sequence | Script | Purpose |
| ---: | --- | --- |
| 0 | [00_FIELD_SOURCE_INVENTORY.sql](00_FIELD_SOURCE_INVENTORY.sql) | Inventory exact 25 source keys and source shapes; includes two deferred Profile fields |
| 1 | [SSP Information System Type QA](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SSP_INFORMATION_SYSTEM_TYPE_SOURCE_TO_PROP.sql) | Existing source-to-persisted-target field/value check; prior owner screenshot had matches |
| 2 | [Request to Begin Assessment QA](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_REQUEST_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | Existing Assessment Plan task-property check; prior owner screenshot had 2,766 matches and other statuses pending classification |
| 3 | [Approval to Begin Assessment QA](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_APPROVAL_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | Assessment Plan root -> task -> prop and resolved picklist check |
| 4 | [Preassessment Review Comments QA](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_PREASSESSMENT_REVIEW_COMMENTS_SOURCE_TO_TASK.sql) | Assessment Plan root -> task remarks **member**, not a prop child |
| 5 | [05_SSP_FIVE_CONTROL_PROPERTIES.sql](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | Exactly five photographed control-summary properties, including four earlier source-key-absent cases |
| 6 | [10_SSP_SIX_COMPONENT_REFERENCES.sql](10_SSP_SIX_COMPONENT_REFERENCES.sql) | Exactly six photographed SSP component-reference fields, parent FACT linkage and identity/type comparison |
| 7 | [20_AR_SIX_FIELD_VALUE_QA.sql](20_AR_SIX_FIELD_VALUE_QA.sql) | Exactly six photographed Assessment Results fields, native observation props and standalone result props |
| 8 | [30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) | Two photographed assessor assignments, party counts/orphans; **UUID identity remains a separate final gate** |
| 9 | [50_SSP_FOUR_ABSENT_KEYS_SOURCE_NAME_DISCOVERY.sql](50_SSP_FOUR_ABSENT_KEYS_SOURCE_NAME_DISCOVERY.sql) | Optional investigation of **only the four** photographed source keys earlier absent; no speculative aliasing |
| 10 | [60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) | Two Profile mappings are DEFERRED: inspect Archer source population only; **cannot target-PASS** |

These are multiple read-only statements, not one stored procedure; run only the scripts for evidence gaps and avoid rerunning already accepted identical checks. The aggregate SQL is not a formal mapper QA run. A single-field sample `VALUE_MATCH` is not complete-dataset conformance.

### Per-field coverage (screenshot order)

| Image row | Exact field | Model / target | Execution status | QA |
| --- | --- | --- | --- | --- |
| 01 | `INFORMATION_SYSTEM_TYPE` | SSP System Characteristics | APPROVED | [SQL](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SSP_INFORMATION_SYSTEM_TYPE_SOURCE_TO_PROP.sql) |
| 02 | `REQUEST_TO_BEGIN_ASSESSMENT` | Assessment Plan task property | APPROVED | [SQL](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_REQUEST_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) |
| 03 | `APPROVAL_TO_BEGIN_ASSESSMENT` | Assessment Plan task property | APPROVED | [SQL](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_APPROVAL_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) |
| 04 | `PREASSESSMENT_REVIEW_COMMENTS` | Assessment Plan task remarks | APPROVED | [SQL](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/sql/SAP_PREASSESSMENT_REVIEW_COMMENTS_SOURCE_TO_TASK.sql) |
| 05 | `PCT_CURRENT_CONTROL_RISK_THRESHOLD` | SSP characteristics property | APPROVED | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) |
| 06 | `PCT_OF_SATISFIED_CONTROLS` | SSP characteristics property | APPROVED | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) |
| 07 | `SECURITY_CONTROL_ASSESSOR_SCA` | SSP responsible-party assignment | APPROVED | [SQL](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) |
| 08 | `LINK_CNSS_CONTROLS_BY_AVAILABILITY_RATING` | SSP characteristics property | APPROVED | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) |
| 09 | `EXPORT_CONTROLLED_DATA_ITARAR_IF_APPLICABLE` | SSP characteristics property | APPROVED | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) |
| 10 | `ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA` | SSP responsible-party assignment | APPROVED | [SQL](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) |
| 11 | `HELPER_ALLOCATED_CONTROLS` | SSP characteristics JSON-text property | APPROVED | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) |
| 12 | `SUBSYSTEMS` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 13 | `SOFTWARE` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 14 | `HARDWARE` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 15 | `INTERCONNECTIONS` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 16 | `INTERCONNECTIONS_CONNECTING_INFORMATION_SYSTEM` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 17 | `SAP_INTAKE_FORM_INTERCONNECTIONS` | SSP components[] reference | APPROVED | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) |
| 19 | `FINDINGS` | Assessment Results props[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 20 | `RISK_ACCEPTANCE_RBDS` | Assessment Results props[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 21 | `PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD` | Assessment Results observations[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 22 | `PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD` | Assessment Results observations[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 23 | `RISK_ASSESSMENT_REPORT` | Assessment Results props[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 24 | `DUE_DATE` | Assessment Results props[] | APPROVED | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) |
| 25 | `ADD_OVERLAY` | Profile | DEFERRED | [SQL](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) |
| unnumbered | `BASELINE_RECOMMENDATION` | Profile | DEFERRED | [SQL](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) |

## Acceptance gates

1. **Populated source vs exact stored OSCAL value**, with source Content ID and correct property/observation/task ownership. Distinguish missing field key from explicit JSON null.
2. **Multi-valued inputs** require full membership comparison; mere target presence is a partial check. References and responsible parties need identity and link verification. For role assignments, count/orphan checks are not a full user-ID -> UUIDv5 comparison.
3. **Source version/snapshot:** duplicate raw Content IDs must be reconciled with notebook source-row selection before alleging a mapping defect. MD5-derived reference identity checks use the repository's `v1_registry_path_instance` contract; mismatches may reflect a different deployed version.
4. **Deferred Profile fields:** report source values and leave target validation `DEFERRED`, never claim zero-missing/passed mappings.
5. **No writes:** No SQL here creates/updates/deletes source, DIM, FACT, registry, or metadata. Running the scripts is inspection only.

## Actual verification vs outstanding

**Performed:** retrieved current CSV and mapper source code; reproduced 25 photographed field names; generated/published read-only QA scripts and reused prior publicly posted field QA. GitHub content readback and static checks are documented in dated OSCAL checkpoints.

**Not performed:** the new queries have not been parsed/executed in Snowflake and have no returned `QA_STATUS` results yet. The 2026-10-23 owner-visible Control Implementation 50-field screenshot is separate historic evidence, not proof this screenshot-specific pack has been run. Existing historical full COMMITs must not be construed as validating newer field mappings.

**Next:** Run 00, then the pending script(s) above; export/paste only `ARCHER_FIELD_NAME`, `QA_STATUS`, and counts to the private project. Reconcile any failures field-by-field before changing mapper code or requesting a COMMIT.
