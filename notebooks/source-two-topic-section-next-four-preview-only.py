# %% Source Two Topic/Section — next 4 optional Catalog properties, DEV PREVIEW ONLY
# Date: 2026-10-15. Copy as ONE new cell into existing DEV Snowflake notebook.
# Prerequisite: load PRIVATE 67-row sources_source_runtime.csv in Notebook Files;
# retain the accepted previous Source Two 62-row mapping snapshot in memory.
# No Cell 7 rerun, source reload, registry SQL, target DIM/FACT writes or COMMIT.
import json

_SOURCE = "source-two-source"
_ROUTE = (_SOURCE, "CATALOG")
_REGISTRY_PATHS = {
    "catalog", "catalog.metadata", "catalog.metadata.props[]",
    "catalog.groups[]", "catalog.groups[].groups[]",
    "catalog.groups[].groups[].groups[]",
}
_NEW = (
    ("DOCUMENT_NUMBER", "APPROVED", "text", "topics",
     "catalog.groups[].props", "document-number"),
    ("TOTAL_NUMBER_OF_SECTIONS", "APPROVED", "direct", "topics",
     "catalog.groups[].props", "section-count"),
    ("SECTION_SHORT_DESCRIPTION", "APPROVED", "text", "sections",
     "catalog.groups[].groups[].props", "short-description"),
    ("TOTAL_NUMBER_OF_SUB_SECTIONS", "APPROVED", "direct", "sections",
     "catalog.groups[].groups[].props", "sub-section-count"),
    ("INFORMATION", "DEFERRED", "text", "sections",
     "catalog.groups[].groups[].parts", "information"),
)
_need = (
    "SOURCE_PROFILES", "SOURCE_INPUTS", "MAPPING_INPUTS", "REGISTRY_INPUT_ROWS",
    "SELECTED_MODELS", "MODEL_CONTRACTS", "ROUTING_METADATA", "CONFIG",
    "load_mapping_rows", "compile_mapping_contexts", "run_oscal_pipeline",
    "_to_python",
)
_missing = [name for name in _need if name not in globals()]
if _missing:
    raise RuntimeError("TOPIC_SECTION_PREVIEW_MISSING_OLD_SESSION: " + ",".join(_missing))

def _gate(ok, code):
    if not ok:
        raise RuntimeError("SOURCE_TWO_TOPIC_SECTION_PREVIEW_BLOCKED_" + code)

_gate(tuple(SELECTED_MODELS) == ("CATALOG",), "CATALOG_ONLY")
_gate(CONFIG.get("EXECUTE_WRITES") is False, "SHARED_WRITES_DISABLED")
_profiles = [p for p in SOURCE_PROFILES if p.get("SOURCE_KEY") == _SOURCE]
_gate(len(_profiles) == 1 and len(SOURCE_PROFILES) == 1,
      "EXACTLY_ONE_SOURCE_TWO_PROFILE")
_profile = _profiles[0]
_gate(_profile.get("MAPPING_FILE") == "sources_source_runtime.csv"
      and tuple(_profile.get("MODEL_KEYS", ())) == ("CATALOG",),
      "MATCHING_CATALOG_CSV_PROFILE")
_old = MAPPING_INPUTS.get(_SOURCE)
_gate(isinstance(_old, list) and len(_old) in (62, 67), "PREVIOUS_62_OR_67_ROW_CONTEXT")
_gate(_SOURCE in SOURCE_INPUTS and isinstance(SOURCE_INPUTS[_SOURCE], dict),
      "SOURCE_TWO_CACHE_REQUIRED")
_lookups = SOURCE_INPUTS[_SOURCE].get("lookups", {})
_frames = _lookups.get("joined_sources", {})
_gate(all(_frames.get(key) is not None for key in ("topics", "sections", "subsections")),
      "THREE_JOINED_LEVELS_REQUIRED")
_reg = [
    r for r in REGISTRY_INPUT_ROWS
    if str(r.get("OSCAL_MODEL_KEY") or "").upper() == "CATALOG"
    and str(r.get("IS_ACTIVE") or "").lower() == "true"
]
_gate(len(_reg) == 6 and {
    str(r.get("NODE_PATH") or "").strip() for r in _reg
} == _REGISTRY_PATHS, "ACCEPTED_SIX_CATALOG_REGISTRY_PATHS")

_candidate = load_mapping_rows(_profile)
_gate(len(_candidate) == 67 and _candidate[:62] == _old[:62],
      "ACCEPTED_62_ROW_PREFIX_UNCHANGED")
if len(_old) == 67:
    _gate(
        [r.get("SOURCE_FIELD_NAME") for r in _old[62:]] ==
            [r.get("SOURCE_FIELD_NAME") for r in _candidate[62:]]
        and all(
            a.get("EXECUTION_STATUS") == b.get("EXECUTION_STATUS")
            for a, b in zip(_old[62:], _candidate[62:])
        ),
        "CURRENT_67_ROW_STATUS_DRIFT"
    )
for _row, (_field, _state, _transform, _binding, _path, _prop) in zip(
        _candidate[62:], _NEW):
    _gate(
        _row.get("SOURCE_FIELD_NAME") == _field
        and _row.get("OSCAL_MODEL") == "Catalog - Group"
        and _row.get("OSCAL_ELEMENT_PATH") == _path
        and _row.get("EXECUTION_STATUS") == _state
        and _row.get("TRANSFORM_ID") == _transform
        and _row.get("LOOKUP_KEY") == _binding
        and _row.get("PROPERTY_NAME") == _prop
        and _row.get("SOURCE_KEY") == _SOURCE,
        "ONLY_REVIEWED_FOUR_ACTIVE_ONE_DEFERRED"
    )

# One targeted source-shape check resolves the screenshot's clipped right edge.
# If the remaining 13 document numbers are not TEXT, do not map them as text.
_count, _null, _typed = 0, 0, 0
for _r in _frames["topics"].to_local_iterator():
    _count += 1
    _doc = _to_python(_r["CURATED_JSON"])
    if isinstance(_doc, str):
        _doc = json.loads(_doc)
    _gate(isinstance(_doc, dict) and "DOCUMENT_NUMBER" in _doc,
          "DOCUMENT_NUMBER_KEY_MISSING_OR_BAD_JSON")
    _v = _doc["DOCUMENT_NUMBER"]
    if _v is None:
        _null += 1
    elif isinstance(_v, str) and _v.strip():
        _typed += 1
    else:
        raise RuntimeError("SOURCE_TWO_TOPIC_SECTION_PREVIEW_BLOCKED_DOCUMENT_NUMBER_NON_TEXT")
_gate((_count, _null, _typed) == (1416, 1403, 13),
      "DOCUMENT_NUMBER_SOURCE_PROFILE_DRIFT")

_new_mapping_inputs = dict(MAPPING_INPUTS)
_new_mapping_inputs[_SOURCE] = _candidate
_contexts = compile_mapping_contexts(
    _new_mapping_inputs, REGISTRY_INPUT_ROWS,
    SOURCE_PROFILES, MODEL_CONTRACTS, ROUTING_METADATA,
)
_gate(len(_contexts) == 1
      and _contexts[0]["source_key"] == _SOURCE
      and _contexts[0]["routing_report"]["STATUS"] == "READY"
      and _contexts[0]["config"].get("EXECUTE_WRITES") is False
      and _contexts[0]["config"]["OSCAL_MODEL"] == "CATALOG"
      and len(_contexts[0]["mapping_rows"]) == 52,
      "EXPECTED_52_COMPILED_CATALOG_RULES")
_new_active = [
    r for r in _contexts[0]["mapping_rows"]
    if r.get("SOURCE_FIELD_NAME") in {r[0] for r in _NEW[:4]}
    and r.get("OWNER_ELEMENT_PATH") in
       {"catalog.groups[]", "catalog.groups[].groups[]"}
]
_gate(len(_new_active) == 4 and not any(
    r.get("OWNER_ELEMENT_PATH") == "catalog.groups[].groups[]"
    and r.get("SOURCE_FIELD_NAME") == "INFORMATION"
    for r in _contexts[0]["mapping_rows"]
), "NEW_FOUR_PROP_LEVELS_AND_DEFERRED_INFORMATION")

print("SOURCE_TWO_NEXT_FOUR_TOPIC_SECTION_CATALOG_PREVIEW")
print("MAPPING_ROWS:", len(_candidate))
print("NEW_ACTIVE_FIELDS:", 4)
print("NEW_DEFERRED_SECTION_INFORMATION:", 1)
print("TOPIC_DOCUMENT_NUMBER_TEXT:", _typed)
print("TOPIC_DOCUMENT_NUMBER_JSON_NULL:", _null)
print("SOURCE_CODE_SCOPE: unchanged 62-rule prefix; next 4 Topic/Section props only")

# Hardcoded PREVIEW even when historical Cell 7 load mode is COMMIT.
NEXT_TOPIC_SECTION_GRAPHS, NEXT_TOPIC_SECTION_REPORT = run_oscal_pipeline(
    SOURCE_INPUTS, _contexts, "PREVIEW"
)
_report = NEXT_TOPIC_SECTION_REPORT
_groups = _report.get("groups") or []
_gate(isinstance(_groups, list) and len(_groups) == 1,
      "ONE_CATALOG_PREVIEW_GROUP_REQUIRED")
_group = _groups[0]
_gate(
    _report.get("mode") == "PREVIEW"
    and _report.get("status") == "PREVIEW_COMPLETE"
    and _report.get("writes_executed") is False
    and _report.get("commit_attempted") is False
    and (_group.get("source"), _group.get("model")) == _ROUTE
    and _group.get("mapping_fingerprint") ==
        _contexts[0]["compiled_plan"]["mapping_fingerprint"],
    "ONLY_ONE_SUCCESSFUL_PREVIEW"
)
_load = _group["load"]
_delta = _load.get("expected_changes") or {}
_d, _f = _delta.get("D") or {}, _delta.get("F") or {}
_gate(
    _load.get("mode") == "PREVIEW"
    and _load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
    and all(_load.get(k) is False for k in
            ("writes_executed", "persisted", "committed", "target_dml_attempted"))
    and all(_load.get(k) is True for k in
            ("pre_write_validation_passed", "validation_passed", "storage_verified"))
    and _load.get("lineage_gaps") == 0
    and _load.get("source_records") == 148
    and _load.get("nodes") == 33679
    and _load.get("edges") == 33531
    and _d == {"INSERTS": 0, "UPDATES": 11982, "UNCHANGED": 21697}
    and _f == {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531}
    and all((_load.get("approved_retirement") or {}).get(k) == 0
            for k in ("nodes", "edges", "source_records")),
    "EXPECTED_TOPIC_SECTION_ONLY_PAYLOAD_DELTA"
)
print("DIM_PREVIEW_CHANGE_COUNTS:", json.dumps(_d, sort_keys=True))
print("FACT_PREVIEW_CHANGE_COUNTS:", json.dumps(_f, sort_keys=True))
print("MAPPING_FINGERPRINT:", _group.get("mapping_fingerprint"))
print("RESULT: PREVIEW_PASSED_NO_TARGET_DML; NEW_FOUR_FIELD_QA_PENDING")
print("No source/registry/DIM/FACT DML or COMMIT. DO NOT run Cell 7 again.")
