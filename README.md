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

## SSP: CIA source-field population and lineage coverage

Run [the read-only CIA field coverage SQL](sql/ssp_security_impact_coverage_and_lineage_readonly.sql) directly in Snowflake DEV. It includes the full configured database/schema/table identifiers, no placeholders, and two checks: approved CIA source fields versus nulls/stored lineage, and records with populated CIA source values but no native `security-impact-level` node. Record-specific values, findings, decisions, and checkpoints stay in the private OSCAL project. The published SQL was reviewed and committed, **not executed against Snowflake**.

**Follow-up (2026-10-12):** [Check source labels, native-element omissions, fallback values, and explicit lineage per populated CIA field](sql/ssp_cia_fallback_value_lineage_check_readonly.sql). This query is read-only and includes no record-specific filter. Review `VALUE_CHECK` and `LINEAGE_CHECK`; do not interpret missing native elements alone as lost source data.

**Latest validation (2026-10-12):** [Summarize SSP CIA fallback value matches and missing lineage by field and overall](sql/ssp_cia_fallback_status_summary_readonly.sql). Read-only Snowflake DEV SQL. Use the `ALL_FIELDS` summary to verify all returned rows, rather than inferring entire-result success from visible screenshot rows.

**Direct-native CIA migration preflight:** [read-only DIM/FACT fallback inventory](sql/ssp_cia_direct_native_migration_preflight_readonly.sql). Use this before attempting a migration from old fallback properties to the new direct native-member mapper. It uses exact DEV table names and performs no writes.

**Next DEV check (2026-10-12):** [Classify direct-native CIA impact and check conflicting Archer labels](sql/ssp_cia_direct_native_impact_and_conflicts_readonly.sql). Run both read-only SELECTs. This estimates complete/partial/all-null source records and detects conflicting populated labels before any migration or COMMIT.

**Obsolete CIA fallback dependency safety (2026-10-12):** [Run read-only FACT relationship audit](sql/ssp_cia_obsolete_fallback_dependency_safety_readonly.sql) before retiring the 91 old fallback property nodes. It checks incoming links, outgoing links, parent ownership and unsafe relationship counts. No DIM/FACT writes are performed; internal record-specific evidence stays in private OSCAL GitHub.
