# %% Source Two — SIX NEW Sub-Section payload fields, PREVIEW ONLY
# Date: 2026-10-14. For ONE new Python cell in the original Snowflake DEV
# notebook, after installing the reviewed private 62-row mapping CSV into
# Notebook Files/sources_source_runtime.csv.
#
# Requires the existing matching seven-cell mapper definitions/source
# snapshots still in this notebook session from the accepted 52-row COMMIT.
# No old QA rerun, registry SQL, approved-rule modification, or target DML.
# The existing guarded PREVIEW loader may create/drop TEMPORARY tables.
import copy
import json

_required_globals = (
    "CONFIG", "SOURCE_PROFILES", "SOURCE_INPUTS", "MAPPING_INPUTS",
    "REGISTRY_INPUT_ROWS", "MODEL_CONTRACTS", "ROUTING_METADATA",
    "SELECTED_MODELS", "load_mapping_rows", "compile_mapping_contexts",
    "run_oscal_pipeline",
)
_missing_symbols = [name for name in _required_globals if name not in globals()]
if _missing_symbols:
    raise RuntimeError(
        "MATCHING_ACCEPTED_52_NOTEBOOK_SESSION_REQUIRED: " +
        ", ".join(_missing_symbols)
    )

def _require(ok, code):
    if not ok:
        raise RuntimeError("SOURCE_TWO_NEXT_SIX_PREVIEW_BLOCKED_" + code)

_source_key = "source-two-source"
_catalog_owner = "catalog.groups[].groups[].groups[]"
_expected_registry_paths = {
    "catalog", "catalog.metadata", "catalog.metadata.props[]",
    "catalog.groups[]", "catalog.groups[].groups[]",
    "catalog.groups[].groups[].groups[]",
}
_next_new_rows = (
    ("SUB_SECTION_DESCRIPTION", "APPROVED", "text", "overview", "parts"),
    ("INFORMATION", "DEFERRED", "text", "information", "parts"),
    ("SUB_SECTION_SHORT_DESCRIPTION", "APPROVED", "text", "short-description", "props"),
    ("SUBSECTION_CRITICALITY_VALUE", "DEFERRED", "direct", "criticality-value", "props"),
    ("SUB_SECTION_MAPPING_STATUS", "APPROVED", "archer-select", "mapping-status", "props"),
    ("NUMBER_OF_CONTROL_STANDARDS_SUB_SECTION_LEVEL", "APPROVED", "direct", "control-count", "props"),
    ("COUNT_OF_CONTROLS", "APPROVED", "direct", "total-controls", "props"),
    ("CONTENT_SOURCE", "APPROVED", "archer-select", "content-source", "props"),
    ("SUB_SECTION_DATE_CREATED", "DEFERRED", "timestamp", "date-created", "props"),
    ("SUB_SECTION_LAST_UPDATED", "DEFERRED", "timestamp", "last-updated", "props"),
)
_require(tuple(SELECTED_MODELS) == ("CATALOG",), "ONLY_CATALOG_SELECTED")
_require(CONFIG.get("EXECUTE_WRITES") is False, "SHARED_WRITE_FLAG")
_profiles = [p for p in SOURCE_PROFILES if p.get("SOURCE_KEY") == _source_key]
_require(len(_profiles) == 1 and len(SOURCE_PROFILES) == 1, "EXACT_ONE_SOURCE_ROUTE")
_profile = _profiles[0]
_require(_profile.get("MAPPING_FILE") == "sources_source_runtime.csv",
         "EXPECTED_LOCAL_MAPPING_FILENAME")
_require(tuple(_profile.get("MODEL_KEYS", ())) == ("CATALOG",),
         "SOURCE_MODEL_BINDING")
_previous = MAPPING_INPUTS.get(_source_key)
_require(isinstance(_previous, list) and len(_previous) == 52,
         "ACCEPTED_52_CSV_SESSION")
_require(_source_key in SOURCE_INPUTS, "CACHED_SOURCE_UNAVAILABLE")
_lookups = SOURCE_INPUTS[_source_key].get("lookups", {})
_require("subsections" in _lookups.get("joined_sources", {}),
         "CACHED_SUBSECTION_SOURCE_UNAVAILABLE")

_active_registry = [
    r for r in REGISTRY_INPUT_ROWS
    if str(r.get("OSCAL_MODEL_KEY", "")).strip().upper() == "CATALOG"
    and str(r.get("IS_ACTIVE", "")).lower() == "true"
]
_require(len(_active_registry) == 6 and {
    str(r.get("NODE_PATH", "")).strip() for r in _active_registry
} == _expected_registry_paths, "ACCEPTED_6_CATALOG_REGISTRY_PATHS")

_candidate = load_mapping_rows(_profile)
_require(len(_candidate) == 62, "STAGED_62_ROW_CSV_REQUIRED")
_require(_candidate[:52] == _previous, "ACCEPTED_52_ROW_PREFIX_CHANGED")
_tail = _candidate[52:]
_require(len(_tail) == len(_next_new_rows), "EXPECTED_EXACT_NEW_FIELDS")
for _row, (_field, _state, _transform, _name, _member) in zip(
        _tail, _next_new_rows):
    _require(
        _row.get("SOURCE_FIELD_NAME") == _field
        and _row.get("EXECUTION_STATUS") == _state
        and _row.get("TRANSFORM_ID") == _transform
        and _row.get("PROPERTY_NAME") == _name
        and _row.get("OSCAL_MODEL") == "Catalog - Group"
        and _row.get("OSCAL_ELEMENT_PATH") == _catalog_owner + "." + _member
        and _row.get("LOOKUP_KEY") == "subsections"
        and _row.get("SOURCE_KEY") == _source_key,
        "UNEXPECTED_NEW_FIELD_MAPPING"
    )
_require(sum(s == "APPROVED" for _, s, *_ in _next_new_rows) == 6,
         "ONLY_SIX_CANDIDATE_ENABLED")

# Use the compiled generic CSV contract and the PREVIOUS source/registry
# snapshot; never modify MAPPING_INPUTS/MAPPING_CONTEXTS/PIPELINE_REPORT.
_next_mapping_inputs = dict(MAPPING_INPUTS)
_next_mapping_inputs[_source_key] = _candidate
_next_contexts = compile_mapping_contexts(
    _next_mapping_inputs, REGISTRY_INPUT_ROWS,
    SOURCE_PROFILES, MODEL_CONTRACTS, ROUTING_METADATA
)
_require(len(_next_contexts) == 1, "SINGLE_CATALOG_COMPILATION")
_next_context = _next_contexts[0]
_require(
    _next_context["source_key"] == _source_key
    and _next_context["config"]["OSCAL_MODEL"] == "CATALOG"
    and _next_context["config"].get("EXECUTE_WRITES") is False
    and _next_context["routing_report"]["STATUS"] == "READY"
    and len(_next_context["mapping_rows"]) == 48,
    "REVIEWED_CATALOG_ROUTE_COMPILATION"
)

print("SOURCE_TWO_NEXT_6_CATALOG_SUBSECTION_PREVIEW")
print("CANDIDATE_MAPPING_ROWS:", len(_candidate))
print("ACTIVE_NEW_MAPPINGS: 6")
print("DEFERRED_NEW_MAPPINGS: 4")
print("NOTE: SUB_SECTION_DESCRIPTION owner-level depth signoff remains pending.")
print("NOTE: Two source TIMESTAMP_NTZ fields remain DEFERRED pending timezone handling.")

# Hardcode the PREVIEW MODE *at the call*, independently of the notebook's
# pre-existing OSCAL_LOAD_MODE string (which may still show old COMMIT).
NEXT_SOURCE_TWO_CATALOG_GRAPHS, NEXT_SOURCE_TWO_CATALOG_REPORT = (
    run_oscal_pipeline(SOURCE_INPUTS, _next_contexts, "PREVIEW")
)
_report = NEXT_SOURCE_TWO_CATALOG_REPORT
_groups = _report.get("groups", [])
_require(
    _report.get("mode") == "PREVIEW"
    and _report.get("status") == "PREVIEW_COMPLETE"
    and _report.get("writes_executed") is False
    and _report.get("commit_attempted") is False
    and len(_groups) == 1,
    "RESULT_MUST_BE_NO_TARGET_DML_PREVIEW"
)
_group = _groups[0]
_load = _group.get("load", {})
_require(
    (_group.get("source"), _group.get("model")) == (_source_key, "CATALOG")
    and _load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
    and _load.get("mode") == "PREVIEW"
    and _load.get("writes_executed") is False
    and _load.get("committed") is False
    and _load.get("persisted") is False
    and _load.get("target_dml_attempted") is False
    and _load.get("pre_write_validation_passed") is True
    and _load.get("storage_verified") is True
    and _load.get("validation_passed") is True
    and _load.get("lineage_gaps") == 0
    and _load.get("source_records") == 148
    and _load.get("nodes") == 33679
    and _load.get("edges") == 33531,
    "EXACT_NO_WRITE_GRAPH_ENVELOPE"
)
_changes = _load.get("expected_changes", {})
_dim, _fact = _changes.get("D", {}), _changes.get("F", {})
_require(
    _dim.get("INSERTS") == 0
    and _fact.get("INSERTS") == 0
    and _fact.get("UPDATES") == 0
    and _fact.get("UNCHANGED") == 33531
    and isinstance(_dim.get("UPDATES"), int)
    and 0 <= _dim["UPDATES"] <= 20000
    and _dim.get("UNCHANGED") == 33679 - _dim["UPDATES"],
    "EXPECTED_ONLY_SUBSECTION_PAYLOAD_UPDATES"
)
print("SOURCE_RECORDS:", _load["source_records"])
print("DIM_CANDIDATES:", _load["nodes"])
print("FACT_RELATIONSHIPS:", _load["edges"])
print("EXPECTED_DIM_INSERTS_UPDATES_UNCHANGED:",
      _dim["INSERTS"], _dim["UPDATES"], _dim["UNCHANGED"])
print("EXPECTED_FACT_INSERTS_UPDATES_UNCHANGED:",
      _fact["INSERTS"], _fact["UPDATES"], _fact["UNCHANGED"])
print("MAPPING_FINGERPRINT:", _group.get("mapping_fingerprint"))
print("PREVIEW_RESULT: PASS_NO_TARGET_DML; FIELD_VALUE_QA_AND_OWNER_REVIEW_PENDING")
print("No source, registry, DIM or FACT target DML or COMMIT.")
