# OSCAL workbench — current read-only diagnostics

This public repository contains read-only diagnostic scripts. Earlier executable pipeline code and historical SQL remain in the private OSCAL repository. Do not publish credentials, actual source records or query-result payloads here.

## Source Two: populated Control Standard ID and title fields

1. Open [the read-only Python cell](notebooks/source-two-control-standards-populated-id-title-readonly.py).
2. Copy it into **one new Python cell** in your connected Snowflake notebook and run **only that cell**.
3. Review `CANDIDATE_COUNTS`, particularly `FIELD_NAME`, `VALUE_TYPE`, `NONEMPTY_SCALAR_RECORDS`, and `DISTINCT_NONEMPTY_SCALAR_VALUES`.

This checks nonempty values; it does not update tables, load OSCAL controls or change the registry.

## SSP: Archer confidentiality field lineage

Open [the read-only lineage SQL](sql/ssp_confidentiality_archer_lineage_readonly.sql) and run the SELECT statements directly in Snowflake DEV. The configured `RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT` table is named explicitly: **no placeholders or setup variables**.

This checks whether the Archer field name `RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY` is stored as a separate `source-field` property and displays the confidentiality value for the same source record. **Live lineage presence has not yet been verified**; a record-level join does not uniquely attribute a value when multiple fields target one OSCAL objective.
