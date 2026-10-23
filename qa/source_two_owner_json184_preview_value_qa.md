# Source Two original-owner value validation

This is mapping-release validation, not an additional daily ETL cell. Daily runs
continue to use the seven mapper cells and their built-in guards.

Use this script only after a successful PREVIEW of the matching 184-rule release.
Expected selected counts are 151 Catalog, 7 Topic Assessment Results, 10 Section
Assessment Results and 16 Subsection Assessment Results.

1. Leave mapper Cells 1–7 unchanged.
2. Add one temporary Python Cell 8 in the same active PREVIEW session.
3. Copy the complete [validation script](source_two_owner_json184_preview_value_qa.py)
   into Cell 8 and run only that cell.
4. The script prints STARTED/COMPLETED phase labels, then the final
   SOURCE_TWO_OWNER_JSON184_PREVIEW_VALUE_QA report. Save the report privately.

If an earlier attempt was canceled, keep its successful PREVIEW session and
replace only the temporary QA cell. Do not rerun Cells 1–7 or change the CSV for
this performance update. If a complete matching QA report is already accepted,
do not repeat it merely to use the optimization.

Acceptance requires result=PASS, error_count=0 and all four sections
owner_json_properties, default_record_permissions,
native_information_criticality and scalar_array_properties to have status=CHECKED. Stop at any error; do not
rerun or commit automatically.

The 25 additions preserve opaque JSON values at their original records. The 21
additional business fields have retained null examples; synthetic positive tests
do not establish populated original-record acceptance.
They do not create OSCAL roles or enforce access permissions. Existing missing,
null and empty-value omission remains unchanged. The script streams retained
preview inputs and graphs using Snowpark retrieval actions; it does not rebuild the mapper, approve or execute
database writes, or establish persisted/full-document conformance. Missing
retained state fails explicitly. Existing accepted releases keep their own
earlier validation evidence.

The audit reuses compact parent/provenance summaries and a bounded decoded-JSON
cache. It still checks every retained value. The cache budget is not a limit on
all audit memory, and cloud fixture tests do not guarantee a native Snowflake
completion time. Missing/stale session state fails closed; do not restart or
rebuild a preview automatically after an audit error.
