# Source One / SSP — seven fallback props: read-only PREVIEW provenance gate.
# 2026-10-15. Paste into ONE NEW PYTHON cell in the ACTIVE Snowflake notebook
# after the original seven cells have completed in PREVIEW.
# This is Python (not SQL): it inspects in-memory MAPPING_CONTEXTS and PIPELINE_REPORT.
# No DML, COMMIT, model rebuild, registry updates, or notebook-file changes.
#
# A PASS proves only that the seven approved mapping rules were selected by
# the same compiled plan fingerprint as the owner-posted preview. It does NOT
# prove that these source fields contain values or that DIM/FACT has been updated.

EXPECTED_FIELDS = (
    "AUTHORIZATION_PACKAGE_SUBMIT_DATE",
    "ATOIATO_EXPIRATION_DATE",
    "LEGACY_SAP_ID",
    "ALTERNATE_SYSTEM_ADMINISTRATOR_SA",
    "SYSTEM_ADMINISTRATOR_SA",
    "ENTITY",
    "BUSINESS",
)
TARGET_PATH = "system-security-plan.system-characteristics.props[]"
EXPECTED_PREVIEW_FINGERPRINT = (
    "d3b2c1b401ad874e062a276e5e1a2f3e79b66ae20a31703c706ec65dbfbe3d69"
)

issues = []
contexts = [
    c for c in MAPPING_CONTEXTS
    if c.get("source_key") == "source-one"
    and c.get("config", {}).get("OSCAL_MODEL") == "SSP"
]
if len(contexts) != 1:
    issues.append("Expected exactly one Source One SSP mapping context")
else:
    ctx = contexts[0]
    selected = ctx.get("mapping_rows", [])
    matches = {
        field: [r for r in selected if r.get("SOURCE_FIELD_NAME") == field]
        for field in EXPECTED_FIELDS
    }
    for field, rows in matches.items():
        if len(rows) != 1:
            issues.append(f"{field}: selected {len(rows)} times (expected 1)")
        elif (
            rows[0].get("EXECUTION_STATUS") != "APPROVED"
            or rows[0].get("CANONICAL_ELEMENT_PATH") != TARGET_PATH
        ):
            issues.append(f"{field}: wrong status or canonical target")
    compiled_fp = ctx.get("compiled_plan", {}).get("mapping_fingerprint")
    if compiled_fp != EXPECTED_PREVIEW_FINGERPRINT:
        issues.append("Compiled plan fingerprint differs from the posted preview")

report = PIPELINE_REPORT
groups = [
    g for g in report.get("groups", [])
    if g.get("source") == "source-one" and g.get("model") == "SSP"
]
if report.get("mode") != "PREVIEW" or report.get("status") != "PREVIEW_COMPLETE":
    issues.append("Latest pipeline report is not a completed PREVIEW")
if len(groups) != 1 or len(report.get("groups", [])) != 1:
    issues.append("Latest report must contain exactly the Source One SSP route")
else:
    group = groups[0]
    load = group.get("load", {})
    if group.get("mapping_fingerprint") != EXPECTED_PREVIEW_FINGERPRINT:
        issues.append("Report fingerprint differs from the posted preview")
    if load.get("status") != "PREVIEW_PASSED_NO_TARGET_DML":
        issues.append("Target-aware PREVIEW did not pass")
    if not (load.get("validation_passed") and load.get("storage_verified")
            and load.get("pre_write_validation_passed")):
        issues.append("Graph, storage, or pre-write validation not passed")
    if load.get("lineage_gaps") != 0:
        issues.append("Nonzero or unavailable lineage gap count")
    if any(load.get(key) is not False for key in
           ("writes_executed", "committed", "target_dml_attempted")):
        issues.append("Preview has unexpected write/commit state")
if report.get("writes_executed") is not False or report.get("commit_attempted") is not False:
    issues.append("Pipeline has unexpected write/commit state")

print("SOURCE_ONE_SEVEN_TBD_PROPS_PRECOMMIT_READONLY_CHECK")
print("Selected field mappings:",
      sum(len(matches.get(field, [])) == 1 for field in EXPECTED_FIELDS)
      if len(contexts) == 1 else 0, "/ 7")
print("Expected preview fingerprint:", EXPECTED_PREVIEW_FINGERPRINT)
print("Issues:", issues)
print("RESULT:", "METADATA_PREVIEW_GATE_PASSED__SOURCE_VALUE_QA_STILL_REQUIRED"
      if not issues else "BLOCKED__DO_NOT_COMMIT")
