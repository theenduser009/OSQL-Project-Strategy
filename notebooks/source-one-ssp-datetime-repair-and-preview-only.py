# SOURCE ONE / SSP — SESSION DATETIME REPAIR + NO-WRITE PREVIEW
# Date: 2026-10-15. Paste this whole file into ONE NEW PYTHON cell
# of the active Snowflake NB_ARCHER_OSCAL_MAPPER_V2 notebook and run once.
#
# Fixes only the notebook Python name collision:
# some cell rebound 'datetime' from module to datetime.datetime class.
# The permanent private Cell 5 fix locally imports its own module alias.
#
# This helper does NOT edit Cell 1-7 source, upload a CSV, run COMMIT,
# or execute target DIM/FACT DML. The existing seven field-value
# source-to-target QA remains necessary before a later authorized COMMIT.

import importlib as _oscal_importlib
import json as _oscal_json

EXPECTED_FIELDS = (
    "AUTHORIZATION_PACKAGE_SUBMIT_DATE",
    "ATOIATO_EXPIRATION_DATE",
    "LEGACY_SAP_ID",
    "ALTERNATE_SYSTEM_ADMINISTRATOR_SA",
    "SYSTEM_ADMINISTRATOR_SA",
    "ENTITY",
    "BUSINESS",
)
EXPECTED_FINGERPRINT = (
    "d3b2c1b401ad874e062a276e5e1a2f3e79b66ae20a31703c706ec65dbfbe3d69"
)
PROPERTY_PATH = "system-security-plan.system-characteristics.props[]"

# Restore the global module binding expected by the already-loaded Cell 5.
datetime = _oscal_importlib.import_module("datetime")
if not (hasattr(datetime, "datetime") and hasattr(datetime, "timezone")):
    raise RuntimeError("DATETIME_MODULE_REPAIR_FAILED")
print("DATETIME_REPAIRED: True")

# Hard stop if the active notebook is not the expected SSP-only,
# seven-field, no-write mapping context from the successful PREVIEW.
_contexts = [
    c for c in MAPPING_CONTEXTS
    if c.get("source_key") == "source-one"
    and c.get("config", {}).get("OSCAL_MODEL") == "SSP"
]
if len(_contexts) != 1 or len(MAPPING_CONTEXTS) != 1:
    raise RuntimeError("BLOCKED: expected exactly one source-one / SSP route")
_context = _contexts[0]
if _context["config"].get("EXECUTE_WRITES") is not False:
    raise RuntimeError("BLOCKED: CONFIG.EXECUTE_WRITES must remain False")
if _context.get("routing_report", {}).get("STATUS") != "READY":
    raise RuntimeError("BLOCKED: SSP mapping route is not READY")
if _context.get("compiled_plan", {}).get("mapping_fingerprint") != EXPECTED_FINGERPRINT:
    raise RuntimeError("BLOCKED: SSP mapping fingerprint differs from accepted PREVIEW")

for _field in EXPECTED_FIELDS:
    _matches = [
        r for r in _context.get("mapping_rows", [])
        if r.get("SOURCE_FIELD_NAME") == _field
        and r.get("EXECUTION_STATUS") == "APPROVED"
        and r.get("CANONICAL_ELEMENT_PATH") == PROPERTY_PATH
    ]
    if len(_matches) != 1:
        raise RuntimeError("BLOCKED: seven-field SSP mapping scope mismatch: " + _field)

print("MAPPING_SCOPE: 7/7, fingerprint matched")
print("MODE: PREVIEW ONLY; TARGET WRITES: DISABLED")

# Pass the mode explicitly. This does NOT use OSCAL_LOAD_MODE, even
# if the existing Cell 7 was left at COMMIT after its failed attempt.
_recovery_graphs, _recovery_report = run_oscal_pipeline(
    SOURCE_INPUTS, MAPPING_CONTEXTS, load_mode="PREVIEW"
)
_recovery_groups = _recovery_report.get("groups", [])
if len(_recovery_groups) != 1:
    raise RuntimeError("BLOCKED: expected one SSP preview group")
_recovery_group = _recovery_groups[0]
_recovery_load = _recovery_group["load"]
if not (
    _recovery_report.get("status") == "PREVIEW_COMPLETE"
    and _recovery_load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
    and _recovery_load.get("validation_passed") is True
    and _recovery_load.get("storage_verified") is True
    and _recovery_load.get("pre_write_validation_passed") is True
    and _recovery_report.get("writes_executed") is False
    and _recovery_report.get("commit_attempted") is False
    and _recovery_load.get("writes_executed") is False
    and _recovery_load.get("target_dml_attempted") is False
):
    raise RuntimeError("BLOCKED: replay PREVIEW did not meet required no-write validations")

print("SSP_RECOVERY_PREVIEW_REPORT")
print(_oscal_json.dumps({
    "status": _recovery_load["status"],
    "source_records": _recovery_load.get("source_records"),
    "nodes": _recovery_load.get("nodes"),
    "edges": _recovery_load.get("edges"),
    "expected_changes": _recovery_load.get("expected_changes"),
    "lineage_gaps": _recovery_load.get("lineage_gaps"),
    "mapping_fingerprint": _recovery_group.get("mapping_fingerprint"),
    "writes_executed": _recovery_report.get("writes_executed"),
    "commit_attempted": _recovery_report.get("commit_attempted"),
}, indent=2, default=str))
print("RESULT: DATETIME_FIXED_PREVIEW_PASSED__SOURCE_VALUE_QA_AND_COMMIT_PENDING")
