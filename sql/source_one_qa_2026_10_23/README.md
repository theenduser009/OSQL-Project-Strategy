# Owner's 29-row "Fields are not found" worksheet — QA handoff

**Updated October 23, 2026. Scope:** ONLY the 29 numbered rows visible in the owner's latest full worksheet photograph. This **supersedes** the earlier cropped screenshot interpretation of 25 fields. There are **28 identifiable Archer-name entries** and **one invalid/misaligned worksheet row #18**. Of the 28, 25 exact names are in the current runtime CSV, 1 name differs in punctuation (`DUE-DATE` screenshot vs `DUE_DATE` runtime), 1 key (`PORTS_PROTOCOLS_AND_SERVICES_MANAGEMENT_PPSM`) has no executable CSV row, and `RECOMMENDED_SECURITY_CATEGORY` has a runtime `BLOCKED_IF_POPULATED` row. (Overall, 27 have executable CSV rows when the spelling difference is resolved; among them two are DEFERRED and one BLOCKED.) **Do not invent or auto-alias row #18.**

**Current repository evidence:** `theenduser009/Oscal-mapping-strategy`, `simplify-metadata-boundary`, code inspected at `8fb070c2f783b7c76d56552f1f488cee5a4f6f41`; exact `Mapping/ARCHER_OSCAL_MAPPINGS.csv` blob `b9f982c445f293f9b5d47cab565194aa29ef8770`. The repository's runtime CSV, not older worksheet paths, is the executable mapping contract. This SQL pack performs **read-only** DEV checks; publication isn't live Snowflake execution or COMMIT acceptance.

## Single handoff for QA

**Start with [00_FIELD_SOURCE_INVENTORY.sql](00_FIELD_SOURCE_INVENTORY.sql)** for all 28 literal screenshot names. Then use each focused SQL below to prove persisted path/value equality. Returning `SOURCE_KEY_ABSENT` or explicit null is not a failed *populated* mapping; `TARGET_PRESENT` without value/identity parity isn't a PASS.

## Exact screenshot rows, preserved in order

| Row | Literal screenshot field | Current CSV status | Executable target (when accepted) | QA SQL | Current evidence/disposition |
| ---: | --- | --- | --- | --- | --- |
| 1 | `INFORMATION_SYSTEM_TYPE` | APPROVED | SSP characteristics.props[] | [SQL](../SSP_INFORMATION_SYSTEM_TYPE_SOURCE_TO_PROP.sql) | Observed matches/null preservation, not full QA |
| 2 | `REQUEST_TO_BEGIN_ASSESSMENT` | APPROVED | Assessment Plan tasks.props[] | [SQL](../SAP_REQUEST_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | 2,766 VALUE_MATCH shown; 47 other statuses remain to classify |
| 3 | `APPROVAL_TO_BEGIN_ASSESSMENT` | APPROVED | Assessment Plan tasks.props[] | [SQL](../SAP_APPROVAL_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | Pending Snowflake value QA |
| 4 | `PREASSESSMENT_REVIEW_COMMENTS` | APPROVED | Assessment Plan tasks.remarks | [SQL](../SAP_PREASSESSMENT_REVIEW_COMMENTS_SOURCE_TO_TASK.sql) | Pending Snowflake task remarks QA |
| 5 | `PCT_CURRENT_CONTROL_RISK_THRESHOLD` | APPROVED | SSP characteristics.props[] | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | SOURCE_KEY_ABSENT in 2,813 inspected records |
| 6 | `PCT_OF_SATISFIED_CONTROLS` | APPROVED | SSP characteristics.props[] | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | SOURCE_KEY_ABSENT in 2,813 inspected records |
| 7 | `SECURITY_CONTROL_ASSESSOR_SCA` | APPROVED | SSP metadata.responsible-parties[] | [SQL](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) | Prior role exists; UUID membership QA pending |
| 8 | `LINK_CNSS_CONTROLS_BY_AVAILABILITY_RATING` | APPROVED | SSP characteristics.props[] | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | SOURCE_KEY_ABSENT in 2,813 inspected records |
| 9 | `EXPORT_CONTROLLED_DATA_ITARAR_IF_APPLICABLE` | APPROVED | SSP characteristics.props[] | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | SOURCE_KEY_ABSENT in 2,813 inspected records |
| 10 | `ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA` | APPROVED | SSP metadata.responsible-parties[] | [SQL](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) | Prior role exists; UUID membership QA pending |
| 11 | `HELPER_ALLOCATED_CONTROLS` | APPROVED | SSP characteristics.props[] | [SQL](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | VALUE_MATCH for 2,813/2,813 in owner screenshot |
| 12 | `SUBSYSTEMS` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | Source JSON null; no populated reference to test |
| 13 | `SOFTWARE` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | 7/7 reference IDs and types matched |
| 14 | `HARDWARE` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | 1/1 reference ID and type matched |
| 15 | `INTERCONNECTIONS` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | 4,444/4,444 references matched |
| 16 | `INTERCONNECTIONS_CONNECTING_INFORMATION_SYSTEM` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | 352/352 references matched |
| 17 | `SAP_INTAKE_FORM_INTERCONNECTIONS` | APPROVED | SSP implementation.components[] | [SQL](10_SSP_SIX_COMPONENT_REFERENCES.sql) | Source JSON null; no populated reference to test |
| 18 | *No field name (row shifted)* | INVALID WORKSHEET ROW | — | Owner correction | Malformed screenshot row, no exact Archer field; owner correction needed |
| 19 | `FINDINGS` | APPROVED | Assessment Results results.props[] | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) | Pending; CSV maps to result props, not native findings[] |
| 20 | `RISK_ACCEPTANCE_RBDS` | APPROVED | Assessment Results results.props[] | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) | Pending; preserve cross-reference ContentId |
| 21 | `PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD` | APPROVED | Assessment Results results.observations[] | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) | Pending observations[] value QA |
| 22 | `PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD` | APPROVED | Assessment Results results.observations[] | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) | Pending observations[] value QA |
| 23 | `RISK_ASSESSMENT_REPORT` | APPROVED | Assessment Results results.props[] | [SQL](20_AR_SIX_FIELD_VALUE_QA.sql) | Pending JSON-text attachment-ID QA |
| 24 | `DUE-DATE` | KEY SPELLING MISMATCH | Assessment Results results.props[] | [SQL](85_DUE_DATE_SCREENSHOT_VS_RUNTIME_KEY.sql) | Literal screenshot DUE-DATE ≠ executable CSV DUE_DATE; check both keys, then value QA |
| 25 | `ADD_OVERLAY` | DEFERRED | Multiple — see notes | [SQL](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) | DEFERRED; source-only; cannot target PASS |
| 26 | `BASELINE_RECOMMENDATION` | DEFERRED | profile.imports[] | [SQL](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) | DEFERRED; source-only; cannot target PASS |
| 27 | `POAMS` | APPROVED | plan-of-action-and-milestones.poam-items[] | [SQL](70_POAMS_REFERENCE_TO_POAM_DIM.sql) | APPROVED, older PREVIEW only; persisted POAM COMMIT/readback unverified |
| 28 | `PORTS_PROTOCOLS_AND_SERVICES_MANAGEMENT_PPSM` | NOT IN CSV | No executable target | [SQL](80_PORTS_AND_RECOMMENDED_CATEGORY_MAPPING_GAPS.sql) | Not present in current executable CSV; source-only, mapping decision if populated |
| 29 | `RECOMMENDED_SECURITY_CATEGORY` | BLOCKED_IF_POPULATED | system-security-plan.system-characteristics.security-impact-level | [SQL](80_PORTS_AND_RECOMMENDED_CATEGORY_MAPPING_GAPS.sql) | BLOCKED_IF_POPULATED; check source and escalate if populated |

## Run these distinct validation statements

| Order | SQL | What it establishes |
| ---: | --- | --- |
| 0 | [00 source field inventory](00_FIELD_SOURCE_INVENTORY.sql) | 28 literal keys, types, missing/null/source-present, and RAW duplicate snapshot warning |
| 1 | [Information System Type](../SSP_INFORMATION_SYSTEM_TYPE_SOURCE_TO_PROP.sql) | Root SSP System Characteristics property name/value |
| 2 | [Request to Begin Assessment](../SAP_REQUEST_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | Archer resolved selection -> Assessment Plan task prop (recheck 47 nonmatches only if needed) |
| 3 | [Approval to Begin Assessment](../SAP_APPROVAL_TO_BEGIN_ASSESSMENT_SOURCE_TO_PROP.sql) | Assessment Plan task prop equality |
| 4 | [Preassessment Review Comments](../SAP_PREASSESSMENT_REVIEW_COMMENTS_SOURCE_TO_TASK.sql) | Native task remarks member equality, not separate props element |
| 5 | [Five SSP Control Implementation properties](05_SSP_FIVE_CONTROL_PROPERTIES.sql) | Already owner-run: HELPER 2,813 match, four exact keys absent; no need identical rerun |
| 6 | [Six SSP Component references](10_SSP_SIX_COMPONENT_REFERENCES.sql) | Already owner-run: 4,804 populated references hash/type match; two fields source-null; no identical rerun |
| 7 | [Assessment Results six fields](20_AR_SIX_FIELD_VALUE_QA.sql) | Result props and observations; pending exact target/result comparison |
| 8 | [Two assessor party relationships](30_SSP_TWO_ASSESSOR_ROLE_RELATIONSHIPS.sql) | Role/cardinality/party graph; UUIDv5 membership remains follow-up |
| 9 | [POAMS reference graph](70_POAMS_REFERENCE_TO_POAM_DIM.sql) | POAM poam-items root/child graph matching; **historical PREVIEW does not prove COMMIT** |
| 10 | [Profile deferred source profiles](60_PROFILE_TWO_DEFERRED_FIELDS_SOURCE_ONLY.sql) | Not mapped; inspect source only |
| 11 | [PPSM & Recommended Category exceptions](80_PORTS_AND_RECOMMENDED_CATEGORY_MAPPING_GAPS.sql) | No executable PPSM mapping; category blocked-if-populated |
| 12 | [DUE-DATE vs DUE_DATE spelling QA](85_DUE_DATE_SCREENSHOT_VS_RUNTIME_KEY.sql) | Literal screenshot/source-name discrepancy; no silent alias |
| Optional | [Four absent Archer field names](50_SSP_FOUR_ABSENT_KEYS_SOURCE_NAME_DISCOVERY.sql) | Owner-review alternatives only; NEVER auto-substitute |

## Minimum acceptance rules to tell the QA team

- `VALUE_MATCH`, `EXPLICIT_NULL_PRESERVED`, `REFERENCE_ID_AND_TYPE_MATCH`: accepted only for the precise checked field/records/representation.
- `SOURCE_KEY_ABSENT`, `SOURCE_EMPTY`, `SOURCE_NULL_OMITTED`: source not populated; do not count as a tested populated-value mapping.
- `POPULATED_SOURCE_TARGET_MISSING`, `VALUE_MISMATCH`, `SOURCE_REFERENCE_ID_INVALID`, `ROLE_ORPHAN`: flag for investigation before owner-approved repair; do not blindly rerun a load.
- `TARGET_PRESENT_SHAPE_OR_MULTI_REVIEW`, `ROLE_GRAPH_AND_COUNT_MATCH_UUID_IDENTITY_REVIEW`: partial QA, not PASS.
- `BLOCKED_IF_POPULATED`, `DEFERRED`, `NOT_IN_RUNTIME_CSV`, `KEY SPELLING MISMATCH`: mapping decisions/metadata cleanup required if the source is populated; these are not target field PASS.
- Source `CONTENT_ID` and referenced component/POAM ContentId must stay distinct. Confirm FACT parent ownership, not only a DIM `props` label. A current notebook version/fingerprint mismatch must be resolved before calling unexpected hash mismatches a code defect.

**Evidence achieved earlier (owner-supplied Snowsight screenshots, October 23):** `INFORMATION_SYSTEM_TYPE` values and explicit nulls demonstrated; `REQUEST_TO_BEGIN_ASSESSMENT` 2,766/2,813 value matches (remaining statuses unclassified); `HELPER_ALLOCATED_CONTROLS` 2,813/2,813 `VALUE_MATCH`; four SSP Control fields exact source keys absent for inspected 2,813; `HARDWARE` 1/1, `SOFTWARE` 7/7, `INTERCONNECTIONS` 4,444/4,444, `INTERCONNECTIONS_CONNECTING_INFORMATION_SYSTEM` 352/352 reference ID/type matches; `SUBSYSTEMS` and `SAP_INTAKE_FORM_INTERCONNECTIONS` source JSON null for 2,813. These are specific QA observations only, not a fresh full Source One COMMIT.

**Still needed:** the outcomes of pending scripts and an owner clarification of workbook row 18. Do not publish private source row values or screenshot images to the public repo. No Snowflake DML, mapper changes or mapping CSV edits were made for this QA pack.
