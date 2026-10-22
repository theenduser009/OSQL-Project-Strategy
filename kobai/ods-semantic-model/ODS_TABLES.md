# ODS table and column dictionary

Date: October 22, 2026. Schema definitions only; no row data or examples.

Use the existing table names below. Database/schema qualification remains internal. The names and types reflect inspected configuration and loader definitions, not a new live database query.

## Model table pairs

| Model | DIM table | DIM primary key | FACT table | FACT primary key |
|---|---|---|---|---|
| `SSP` | `DIM_OSCAL_SSP_ELEMENT` | `PK_OSCAL_SSP_ELEMENT_HASH` | `FACT_OSCAL_SSP_DEPENDENCY` | `PK_FACT_OSCAL_DEPENDENCY_HASH` |
| `SECURITY_ASSESSMENT_PLAN` | `DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT` | `PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH` | `FACT_OSCAL_ASSESSMENT_PLAN_DEPENDENCY` | `PK_FACT_OSCAL_ASSESSMENT_PLAN_DEPENDENCY_HASH` |
| `ASSESSMENT_RESULTS` | `DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT` | `PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH` | `FACT_OSCAL_ASSESSMENT_RESULTS_DEPENDENCY` | `PK_FACT_OSCAL_ASSESSMENT_RESULTS_DEPENDENCY_HASH` |
| `POAM` | `DIM_OSCAL_POAM_ELEMENT` | `PK_DIM_OSCAL_POAM_ELEMENT_HASH` | `FACT_OSCAL_POAM_DEPENDENCY` | `PK_FACT_OSCAL_POAM_DEPENDENCY_HASH` |
| `CATALOG` | `DIM_OSCAL_CATALOG_ELEMENT` | `PK_DIM_OSCAL_CATALOG_ELEMENT_HASH` | `FACT_OSCAL_CATALOG_DEPENDENCY` | `PK_FACT_OSCAL_CATALOG_DEPENDENCY_HASH` |

All listed primary keys use `BINARY(16)`. Each table pair is a distinct physical binding. SSP key names must not be generated from the other naming patterns.

## Shared DIM columns

| Column | Type | Meaning |
|---|---|---|
| `ELEMENT_TYPE` | `VARCHAR(64)` | Element-kind discriminator; combine with owner path and model. |
| `OSCAL_UUID` | `VARCHAR(32)` | Warehouse UUID stored without hyphens; not every payload has a uuid member. |
| `METADATA_JSON` | `VARIANT` | Element payload; distinguish scalar members from inline collections and separate child elements. |
| `SOURCE_SYSTEM_NAME` | `VARCHAR(100)` | ODS provenance column definition only; no values or upstream connection instructions are published. |
| `SOURCE_TABLE_NAME` | `VARCHAR(128)` | ODS provenance column definition only; no upstream object identifiers are published. |
| `SOURCE_RECORD_ID` | `VARCHAR(128)` | ODS provenance identifier; not the primary key for every element and not necessarily a nested item's identifier. |
| `DW_PIPELINE_RUN_ID` | `VARCHAR(64)` | Technical load lineage; not a business join key. |
| `DW_LOAD_TIMESTAMP` | `TIMESTAMP_TZ(9)` | Technical load timestamp; not automatically a business effective date. |
| `DW_LOAD_TIMESTAMP_TZ` | `TIMESTAMP_TZ(9)` | Technical timezone-aware load timestamp. |

These nine shared columns plus the model-specific primary key make up the inspected DIM layout.

## Shared FACT columns

| Column | Type | Meaning |
|---|---|---|
| `FK_SOURCE_ELEMENT_HASH` | `BINARY(16)` | Parent endpoint for CONTAINS. |
| `FK_TARGET_ELEMENT_HASH` | `BINARY(16)` | Child endpoint for CONTAINS. |
| `DEPENDENCY_TYPE` | `VARCHAR(32)` | Physical relationship label; filter CONTAINS for hierarchy. |
| `SOURCE_OSCAL_UUID` | `VARCHAR(32)` | Parent warehouse UUID for endpoint consistency checks. |
| `TARGET_OSCAL_UUID` | `VARCHAR(32)` | Child warehouse UUID for endpoint consistency checks. |

These five shared columns plus the model-specific primary key make up the inspected FACT layout.

The loader expects non-null primary keys and FACT columns; non-key DIM columns are nullable. These are contract expectations to verify internally, not a claim that constraints are enforced by the deployed database.

## Join and ownership contract

For a model, let `p` and `c` be parent and child aliases of its DIM, and `f` an alias of its FACT. Resolve:

```text
f.FK_SOURCE_ELEMENT_HASH = p.<model DIM primary key>
f.FK_TARGET_ELEMENT_HASH = c.<model DIM primary key>
f.DEPENDENCY_TYPE = 'CONTAINS'
f.SOURCE_OSCAL_UUID = p.OSCAL_UUID
f.TARGET_OSCAL_UUID = c.OSCAL_UUID
```

Keep model and owning-document context on both endpoints. Reuse binary keys; any text conversion in an authorized adapter must use the same hexadecimal encoding for parent, child, and FACT endpoints. Do not join by name or a shared provenance identifier alone.

## Lineage and exposure boundary

`SOURCE_SYSTEM_NAME`, `SOURCE_TABLE_NAME`, and `SOURCE_RECORD_ID` are names of columns already in the ODS contract. Their contents are not published. These definitions do not disclose upstream objects or authorize any traversal outside ODS. Technical audit columns describe load lineage only; their actual values and any business-effective-date interpretation stay internal.

Neither a separate lineage table nor an ODS element-registry table is asserted. Full path and instance columns are not part of this DIM contract; obtain an approved ODS-only path definition or internally resolved adapter metadata where necessary. No sample rows or SQL result exports are requested.
