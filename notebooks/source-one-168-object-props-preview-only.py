# %% Source One SSP: seven object-valued controls -> JSON-text props — PREVIEW ONLY
# October 15, 2026. One NEW Python cell in the SAME DEV notebook session.
# Prerequisite: copy/run UPDATED canonical Cell 3 from the OSCAL GitHub branch.
# Does not reload any source, reupload a CSV, execute other Cells 1-7, or COMMIT.
# Existing Notebook Files CSV remains untouched; this PREVIEW tests a local
# in-memory candidate overlay of precisely seven mappings (original 168 rules).
# Before a future COMMIT, upload/stage the authoritative updated GitHub CSV and
# obtain a separate matching accepted PREVIEW and explicit owner authorization.
import copy
import json

_FIELDS = (
    "ALLOCATE_BASELINE_CONTROLS",
    "ARCHIVE_CONTROLS",
    "CONTROL_RISK_APPETITE",
    "HELPER_ALLOCATED_CONTROLS",
    "CONTROL_RISK_THRESHOLD_HELPER",
    "FULL_CONTROL_ASSESSMENT_HELPER",
    "_CURRENT_CONTROL_RISK_THRESHOLD",
)
_OWNER = "system-security-plan.system-characteristics.props[]"
_EXPECTED_OLD_FINGERPRINT = (
    "047fc34330eadcfd4bea0b0b7a34ef760b2fddc033dba6404e5a3a7de92df576"
)
_REQUIRED = (
    "MAPPING_INPUTS", "MAPPING_CONTEXTS", "SOURCE_INPUTS",
    "SOURCE_PROFILES", "REGISTRY_INPUT_ROWS", "MODEL_CONTRACTS",
    "ROUTING_METADATA", "SELECTED_MODELS", "CONFIG",
    "compile_mapping_contexts", "run_oscal_pipeline",
)
_missing = [name for name in _REQUIRED if name not in globals()]
if _missing:
    raise RuntimeError("SSP_JSON_PREVIEW_STOP_MISSING_CACHED_SESSION: " + ",".join(_missing))


def _need(ok, name):
    if not ok:
        raise RuntimeError("SSP_JSON_PREVIEW_STOP_" + name)


_need(tuple(SELECTED_MODELS) == ("SSP",), "SOURCE_ONE_SSP_ONLY")
_need(CONFIG.get("EXECUTE_WRITES") is False, "SHARED_WRITES_MUST_STAY_FALSE")
_need(set(MAPPING_INPUTS) == {"source-one"} and set(SOURCE_INPUTS) == {"source-one"},
      "ONLY_SOURCE_ONE_CACHED")
_need(len(SOURCE_PROFILES) == 1
      and SOURCE_PROFILES[0].get("SOURCE_KEY") == "source-one"
      and tuple(SOURCE_PROFILES[0].get("MODEL_KEYS", ())) == ("SSP",),
      "ONE_SOURCE_ONE_SSP_PROFILE")
_original = MAPPING_INPUTS["source-one"]
_need(isinstance(_original, list) and len(_original) == 168,
      "EXPECTED_168_CACHED_MAPPING_ROWS")
_source = SOURCE_INPUTS["source-one"].get("source_df")
_need(_source is not None and hasattr(_source, "to_local_iterator"),
      "ORIGINAL_CACHED_CURATED_JSON_UNAVAILABLE")
_old_ctx = [c for c in MAPPING_CONTEXTS if c.get("source_key") == "source-one"
            and c.get("config", {}).get("OSCAL_MODEL") == "SSP"]
_need(len(_old_ctx) == 1 and len(MAPPING_CONTEXTS) == 1
      and _old_ctx[0]["routing_report"]["STATUS"] == "READY"
      and _old_ctx[0]["config"].get("EXECUTE_WRITES") is False,
      "ORIGINAL_COMPILED_SSP_ROUTE_NOT_READY")
_old_fp = _old_ctx[0].get("compiled_plan", {}).get("mapping_fingerprint")
_need(_old_fp == _EXPECTED_OLD_FINGERPRINT,
      "OLD_FINGERPRINT_DIFFERENT_STOP_AND_REVIEW")
_need(_old_ctx[0]["compiled_plan"].get("release") ==
      "lean-csv-registry-v17-cia-null-lineage",
      "EXPECTED_V17_MAPPER")

# The authoritative new 168-row CSV already exists in the private GitHub
# simplify-metadata-boundary branch. Only overlay its seven reviewed transform
# changes into the original frozen in-memory mappings for the PREVIEW.
_candidate = copy.deepcopy(_original)
for _field in _FIELDS:
    _rows = [r for r in _candidate if r.get("SOURCE_FIELD_NAME") == _field]
    _need(len(_rows) == 1, "MISSING_OR_DUPLICATE_" + _field)
    _r = _rows[0]
    _need(
        _r.get("OSCAL_ELEMENT_PATH") == _OWNER
        and _r.get("SOURCE_KEY") == "source-one"
        and _r.get("EXECUTION_STATUS") == "APPROVED"
        and _r.get("TRANSFORM_ID") == "direct"
        and _r.get("NULL_POLICY") == "preserve"
        and (_r.get("VALUE_SOURCE") or "FIELD") == "FIELD",
        "UNEXPECTED_OR_ALREADY_CHANGED_" + _field,
    )
    _r["TRANSFORM_ID"] = "json-text"
_need(len(_candidate) == 168
      and sum(a != b for a, b in zip(_original, _candidate)) == 7
      and MAPPING_INPUTS["source-one"] == _original,
      "CHANGED_ONLY_SEVEN_RULES")

# This compiler must be the updated maintained GitHub Cell 3 which allows the
# existing json-text transform + NULL_POLICY=preserve for a property.
# If older Cell 3 is still active, it will refuse this scope BEFORE any graph.
_ctxs = compile_mapping_contexts(
    {"source-one": _candidate}, REGISTRY_INPUT_ROWS,
    SOURCE_PROFILES, MODEL_CONTRACTS, ROUTING_METADATA,
)
_need(len(_ctxs) == 1 and _ctxs[0]["source_key"] == "source-one"
      and _ctxs[0]["config"]["OSCAL_MODEL"] == "SSP"
      and _ctxs[0]["config"]["EXECUTE_WRITES"] is False,
      "UNEXPECTED_CANDIDATE_SCOPE")
if _ctxs[0]["routing_report"]["STATUS"] != "READY":
    raise RuntimeError(
        "SSP_JSON_PREVIEW_STOP_UPDATED_CELL3_NOT_ACTIVE_OR_MAPPING_BLOCKED: "
        + json.dumps(_ctxs[0]["routing_report"].get("REASON_COUNTS", {}),
                     sort_keys=True)
    )
_rules = [
    r for r in _ctxs[0]["mapping_rows"]
    if r.get("SOURCE_FIELD_NAME") in _FIELDS
    and r.get("OWNER_ELEMENT_PATH") == _OWNER
]
_need(len(_rules) == 7 and {r["SOURCE_FIELD_NAME"] for r in _rules} == set(_FIELDS),
      "EXACT_SEVEN_COMPILED_PROPS_REQUIRED")
_need(all(r["TRANSFORM_ID"] == "json-text"
              and r.get("REPRESENTATION") == "properties"
              and r.get("REPRESENTATION_PARAMS", {}).get("preserve_null") is True
              for r in _rules),
      "COMPILED_JSON_TEXT_NULL_PRESERVE_MISMATCH")
_fp = _ctxs[0]["compiled_plan"]["mapping_fingerprint"]
_need(bool(_fp) and _fp != _old_fp, "EXPECTED_NEW_CANDIDATE_FINGERPRINT")
print("SOURCE_ONE_SSP_168_OBJECT_JSON_TEXT_PREVIEW_ONLY")
print("LOADED_MAPPING_RECORDS:", len(_candidate))
print("CHANGED_TRANSFORMS:", len(_rules))
print("NULL_POLICY:", "preserve")
print("PREVIOUS_MAPPING_FINGERPRINT:", _old_fp)
print("CANDIDATE_MAPPING_FINGERPRINT:", _fp)
print("CANDIDATE_NOT_PERSISTED_TO_NOTEBOOK_FILES: TRUE")
print("NO SOURCE RELOAD, NO REGISTRY WRITE, NO TARGET DIM/FACT COMMIT.")

# Exactly ONE explicit, hardcoded PREVIEW using the cached selected source.
# The loader may use session-local temporary validation tables, but this call
# never requests target DIM/FACT DML or a database COMMIT.
try:
    SSP_OBJECT_PREVIEW_GRAPHS, SSP_OBJECT_PREVIEW_REPORT = run_oscal_pipeline(
        SOURCE_INPUTS, _ctxs, "PREVIEW"
    )
except Exception as exc:
    print("RESULT: SSP_OBJECT_JSON_PREVIEW_FAILED_BEFORE_ACCEPTANCE")
    if hasattr(exc, "report") and isinstance(exc.report, dict):
        print("PREVIEW_STATUS:", exc.report.get("status"))
        print("ERROR_TYPE:", exc.report.get("error_type"))
        print("ERROR_MESSAGE:", exc.report.get("error_message"))
        print("WRITES_EXECUTED:", exc.report.get("writes_executed"))
        print("COMMIT_ATTEMPTED:", exc.report.get("commit_attempted"))
    raise
_report = SSP_OBJECT_PREVIEW_REPORT
_groups = _report.get("groups", [])
_need(_report.get("mode") == "PREVIEW"
      and _report.get("status") == "PREVIEW_COMPLETE"
      and _report.get("writes_executed") is False
      and _report.get("commit_attempted") is False
      and len(_groups) == 1
      and (_groups[0].get("source"), _groups[0].get("model"))
          == ("source-one", "SSP"),
      "EXPECTED_ONLY_NONWRITING_SSP_PREVIEW")
_load = _groups[0]["load"]
_need(_load.get("mode") == "PREVIEW"
      and _load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
      and _load.get("writes_executed") is False
      and _load.get("committed") is False
      and _load.get("persisted") is False
      and _load.get("target_dml_attempted") is False,
      "SSP_PREVIEW_DID_NOT_PASS_NO_DML")
print("PREVIEW_STATUS:", _load.get("status"))
print("CANDIDATE_NODES:", _load.get("nodes"))
print("CANDIDATE_EDGES:", _load.get("edges"))
print("LINEAGE_GAPS:", _load.get("lineage_gaps"))
print("EXPECTED_CHANGES:", json.dumps(_load.get("expected_changes"), sort_keys=True))
print("WRITES_EXECUTED:", _load.get("writes_executed"))
print("COMMITTED:", _load.get("committed"))
print("RESULT: PREVIEW_PASSED_NO_TARGET_DML_JSON_TEXT_SEVEN_FIELDS")
print("NEXT: original Archer value-to-preview-prop QA and staged CSV parity.")
print("DO NOT COMMIT. This is a temporary in-memory candidate overlay, not"
      " the final CSV-loaded deployment preview.")
