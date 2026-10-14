# %% Source Two six-field Sub-Section DEV COMMIT — WRITES TARGET DIM/FACT
# Date: 2026-10-14. SINGLE-RUN owner-executed COMMIT, not a PREVIEW or QA.
# Prerequisites: exactly matching accepted six-field RAW QA and DEV PREVIEW
# are still in this Snowflake notebook session; revised guarded Cell 6 has
# been installed and executed. There is NO source reload or graph rebuild.
# IMPORTANT: Stop other Catalog target writers; snapshot checks do not
# physically lock Snowflake tables. NEVER retry blindly after any exception.
import json

_ROUTE = ("source-two-source", "CATALOG")
_PINNED = {
    "D": {"INSERTS": 0, "UPDATES": 20000, "UNCHANGED": 13679},
    "F": {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531},
}
_FIELDS = {
    "SUB_SECTION_DESCRIPTION": ("parts", "overview", "prose-direct"),
    "SUB_SECTION_SHORT_DESCRIPTION": ("props", "short-description", "text"),
    "SUB_SECTION_MAPPING_STATUS": ("props", "mapping-status", "archer-select"),
    "NUMBER_OF_CONTROL_STANDARDS_SUB_SECTION_LEVEL": ("props", "control-count", "direct"),
    "COUNT_OF_CONTROLS": ("props", "total-controls", "direct"),
    "CONTENT_SOURCE": ("props", "content-source", "archer-select"),
}
_DEFERRED = {
    "INFORMATION", "SUBSECTION_CRITICALITY_VALUE",
    "SUB_SECTION_DATE_CREATED", "SUB_SECTION_LAST_UPDATED",
}
_NEEDED = (
    "validate_and_load_oscal", "_qa_graphs", "_qa_preview_source",
    "_report", "_result", "_mismatch_total", "_prose_delta",
    "_counts", "_nodes", "_original", "MODEL_GRAPHS",
    "PIPELINE_REPORT", "SELECTED_MODELS",
)
_missing = [k for k in _NEEDED if k not in globals()]
if _missing:
    raise RuntimeError("COMMIT_BLOCKED_MISSING_ACCEPTED_QA_STATE: " + ",".join(_missing))

def _require(cond, code):
    if not cond:
        raise RuntimeError("SOURCE_TWO_SIXFIELD_DEV_COMMIT_BLOCKED_" + code)

_require(
    getattr(validate_and_load_oscal, "_approved_delta_guard_release", None)
        == "exact-D-F-delta-prebegin-and-intransaction-v1",
    "REVISED_GUARDED_CELL_6_NOT_INSTALLED"
)
_require(tuple(SELECTED_MODELS) == ("CATALOG",), "CATALOG_ONLY")
_require(_qa_preview_source == "STANDARD_CELL_7", "QA_MUST_VERIFY_CELL7")
_require(_qa_graphs is MODEL_GRAPHS and _report is PIPELINE_REPORT,
         "QA_GRAPH_CONTEXT_NO_LONGER_MATCHES_PREVIEW")
_require(
    _result == "PASS_EXACT_SIX_FIELD_SOURCE_PARITY"
    and _mismatch_total == 0 and _prose_delta == 0
    and len(_nodes) == 20000 and len(_original) == 20000
    and set(_counts) == set(_FIELDS)
    and _counts["SUB_SECTION_DESCRIPTION"]["SOURCE_POPULATED"] == 19962
    and all(v["MISMATCHES"] == 0 for v in _counts.values())
    and all(v["DIRECT_PROSE_DIFFERS_FROM_RAW"] == 0 for v in _counts.values()),
    "SIX_FIELD_RAW_FIDELITY_QA_NOT_ACCEPTED"
)
_groups = _report.get("groups", []) if isinstance(_report, dict) else []
_require(
    _report.get("mode") == "PREVIEW"
    and _report.get("status") == "PREVIEW_COMPLETE"
    and _report.get("writes_executed") is False
    and _report.get("commit_attempted") is False
    and len(_groups) == 1
    and (_groups[0].get("source"), _groups[0].get("model")) == _ROUTE
    and _ROUTE in _qa_graphs,
    "SINGLE_ACCEPTED_NONWRITING_ROUTE"
)
_load = _groups[0].get("load") or {}
_changes = _load.get("expected_changes") or {}
_require(
    all(_changes.get(kind) == approved
        for kind, approved in _PINNED.items())
    and _load.get("mode") == "PREVIEW"
    and _load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
    and all(_load.get(k) is False
            for k in ("target_dml_attempted", "committed",
                      "persisted", "writes_executed"))
    and all(_load.get(k) is True
            for k in ("pre_write_validation_passed", "validation_passed",
                      "storage_verified"))
    and _load.get("source_records") == 148
    and _load.get("nodes") == 33679
    and _load.get("edges") == 33531
    and _load.get("lineage_gaps") == 0
    and all((_load.get("approved_retirement") or {}).get(k) == 0
            for k in ("nodes", "edges", "source_records")),
    "EXACT_APPROVED_PREVIEW_CHANGE_ENVELOPE"
)
_graph = _qa_graphs[_ROUTE]
_ctx = _graph.get("context", {})
_plan = _ctx.get("compiled_plan") or {}
_cfg = _ctx.get("config") or {}
_stored = _cfg.get("STORAGE_CONTRACT") or {}
_rules = [row for row in _ctx.get("mapping_rows", [])
          if row.get("OWNER_ELEMENT_PATH") == "catalog.groups[].groups[].groups[]"]
_lookup = {row["SOURCE_FIELD_NAME"]: row for row in _rules
           if row.get("SOURCE_FIELD_NAME") in _FIELDS}
_require(
    len(_ctx.get("mapping_rows", [])) == 48
    and len(_rules) == 10
    and len(_lookup) == 6
    and all(
        _lookup[field].get("FIELD_RELATIVE_PATH") == member
        and _lookup[field].get("TRANSFORM_ID") == transform
        and _lookup[field].get("REPRESENTATION_PARAMS", {}).get("property_name") == name
        and _lookup[field].get("LOOKUP_KEY") == "subsections"
        for field, (member, name, transform) in _FIELDS.items()
    )
    and not _DEFERRED.intersection(r.get("SOURCE_FIELD_NAME") for r in _rules)
    and _plan.get("release") == "lean-csv-registry-v17-cia-null-lineage"
    and bool(_plan.get("mapping_fingerprint"))
    and _plan.get("mapping_fingerprint") == _groups[0].get("mapping_fingerprint")
    and _cfg.get("OSCAL_MODEL") == "CATALOG"
    and _cfg.get("SOURCE_SYSTEM_NAME") == "ARCHER"
    and _cfg.get("SOURCE_TABLE_NAME") == "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW"
    and _cfg.get("EXECUTE_WRITES") is False
    and _cfg.get("LINEAGE_GAP_COUNT", 0) == 0
    and _cfg.get("ENABLE_APPROVED_SSP_CIA_RETIREMENT", False) is False
    and not _cfg.get("ONE_TIME_RETIREMENT_SPEC")
    and _cfg.get("OBSOLETE_ROW_POLICY", "BLOCK") == "BLOCK"
    and _stored.get("VERIFIED") is True
    and _stored.get("MODEL_KEY") == "CATALOG",
    "EXACT_CORRECTED_COMPILED_MAPPING_AND_SAFE_FLAGS"
)

_dim_target = _stored.get("TARGET_DIM")
_fact_target = _stored.get("TARGET_FACT")
_require(
    isinstance(_dim_target, str) and isinstance(_fact_target, str)
    and _dim_target.upper() == _dim_target
    and _fact_target.upper() == _fact_target
    and len(_dim_target.split(".")) == 3 and len(_fact_target.split(".")) == 3
    and _dim_target.split(".")[:2] == _fact_target.split(".")[:2]
    and _dim_target.split(".")[0].endswith("_DEV")
    and _dim_target.endswith(".DIM_OSCAL_CATALOG_ELEMENT")
    and _fact_target.endswith(".FACT_OSCAL_CATALOG_DEPENDENCY"),
    "DEV_CATALOG_TARGET_ONLY"
)

# Do not take a new mapping or source snapshot; the exact graph whose
# 20,000 child values were independently checked is the candidate to commit.
# Stage/temp checks and actual target changes are re-validated by Cell 6.
_cfg_to_commit = dict(_cfg)
_cfg_to_commit["EXECUTE_WRITES"] = True
_cfg_to_commit["APPROVED_COMMIT_CHANGE_ENVELOPE"] = {
    k: dict(v) for k, v in _PINNED.items()
}
print("SOURCE_TWO_SIXFIELD_GUARDED_DEV_COMMIT")
print("ROUTE:", "source-two-source / CATALOG")
print("APPROVED_CHANGES:", json.dumps(_PINNED, sort_keys=True))
print("SOURCE_QA:", _result)
print("MAPPING_FINGERPRINT:", _plan["mapping_fingerprint"])
print("PREWRITE_GUARD: exact count checked before BEGIN and before first MERGE")
print("IMPORTANT: THIS CELL EXECUTES DEV TARGET WRITES; DO NOT RE-RUN.")
# The following is the ONLY intentional target-writing call in this cell.
_result_commit = validate_and_load_oscal(
    _graph["nodes"], _graph["edges"], _cfg_to_commit
)
print("SOURCE_TWO_SIXFIELD_DEV_COMMIT_RESULT")
print(json.dumps({
    "status": _result_commit.get("status"),
    "release": _result_commit.get("release"),
    "committed": _result_commit.get("committed"),
    "persisted": _result_commit.get("persisted"),
    "writes_executed": _result_commit.get("writes_executed"),
    "approved_commit_delta_checked": _result_commit.get("approved_commit_delta_checked"),
    "expected_changes": _result_commit.get("expected_changes"),
    "verification": _result_commit.get("verification"),
    "temporary_cleanup": _result_commit.get("temporary_cleanup"),
}, sort_keys=True, default=str))
_require(
    _result_commit.get("status") == "COMMITTED_AND_VERIFIED"
    and _result_commit.get("committed") is True
    and _result_commit.get("persisted") is True
    and _result_commit.get("writes_executed") is True
    and _result_commit.get("approved_commit_delta_checked") is True
    and _result_commit.get("expected_changes") == _PINNED
    and all(_result_commit.get("verification", {}).get(kind, {}).get(k) == 0
            for kind in ("DIM", "FACT") for k in ("INSERTS", "UPDATES")),
    "POST_COMMIT_READBACK_NOT_ACCEPTED_DO_NOT_RETRY"
)
print("RESULT: SOURCE_TWO_SIXFIELD_DEV_COMMITTED_AND_READBACK_VERIFIED")
print("Never rerun this COMMIT cell. Move to the next mapping batch.")
