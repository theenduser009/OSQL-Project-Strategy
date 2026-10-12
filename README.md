# OSCAL workbench — current read-only diagnostics

This public repository contains only sanitized, read-only inspection scripts. Earlier executable pipeline code and historical SQL remain in the private OSCAL repository. Do not publish client identifiers, record values, or internal database paths here.

## Source Two: populated Control Standard ID and title fields

1. Open [the read-only Python cell](notebooks/source-two-control-standards-populated-id-title-readonly.py).
2. Copy it into **one new Python cell** in your connected Snowflake notebook and run **only that cell**.
3. Share the `CANDIDATE_COUNTS` output, particularly `FIELD_NAME`, `VALUE_TYPE`, `NONEMPTY_SCALAR_RECORDS`, and `DISTINCT_NONEMPTY_SCALAR_VALUES`.

This checks *nonempty values*, not only whether the source JSON contains a field name. It does not update tables, load OSCAL controls, or issue registry changes.

## SSP: Archer confidentiality field lineage

Open [the read-only lineage SQL](sql/ssp_confidentiality_archer_lineage_readonly.sql). Replace the `SSP_DIM_TABLE` setting with the authorized DEV SSP DIM table, then run the two SELECT queries in Snowflake.

This checks whether the Archer field name `RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY` is stored as a separate `source-field` property and shows its record-associated OSCAL confidentiality value. **The current deployed lineage shape and live data are not verified**, and matching a record does not uniquely attribute a target value when multiple source fields map to it.
