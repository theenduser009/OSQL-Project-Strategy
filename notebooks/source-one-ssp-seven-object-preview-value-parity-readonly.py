# %% SSP 168-row seven-OBJECT PREVIEW value + parent/FACT parity — READ ONLY
# Date: 2026-10-15. ONE new Snowflake DEV Python cell in the SAME successful
# Source One SSP PREVIEW session. Open GitHub, copy whole file, paste, run.
# No source reload, graph rebuild, registry writes, DIM/FACT target DML or COMMIT.
# Prints ONLY aggregates, paths, version statuses. Never source values or Content IDs.
import hashlib
import json
from collections import Counter
from decimal import Decimal
from snowflake.snowpark.functions import col as _oscal_col

_OWNER = "system-security-plan.system-characteristics.props[]"
_PARENT = "system-security-plan.system-characteristics"
_ROUTE = ("source-one", "SSP")
_OLD_FP = "047fc34330eadcfd4bea0b0b7a34ef760b2fddc033dba6404e5a3a7de92df576"
_GIT_CSV_BLOB = "b9f982c445f293f9b5d47cab565194aa29ef8770"
_FIELDS = (
    "ALLOCATE_BASELINE_CONTROLS",
    "ARCHIVE_CONTROLS",
    "CONTROL_RISK_APPETITE",
    "HELPER_ALLOCATED_CONTROLS",
    "CONTROL_RISK_THRESHOLD_HELPER",
    "FULL_CONTROL_ASSESSMENT_HELPER",
    "_CURRENT_CONTROL_RISK_THRESHOLD",
)
_EXPECTED_D = {"INSERTS": 50634, "UPDATES": 0, "UNCHANGED": 829006}
_EXPECTED_F = {"INSERTS": 50634, "UPDATES": 0, "UNCHANGED": 826193}


def _stop(ok, code):
    if not ok:
        raise RuntimeError("SSP_SEVEN_OBJECT_PARITY_STOP_" + code)


for _required in ("SOURCE_INPUTS", "MAPPING_INPUTS", "SOURCE_PROFILES",
                  "SELECTED_MODELS", "CONFIG", "_to_python", "_metadata_parse",
                  "resolve_json_path", "_has_value", "_stable_property_name"):
    _stop(_required in globals(), "MISSING_SESSION_STATE_" + _required)
_stop(tuple(SELECTED_MODELS) == ("SSP",), "NOT_SSP_ONLY")
_stop(CONFIG.get("EXECUTE_WRITES") is False, "WRITES_FLAG_MUST_BE_FALSE")
_stop(set(SOURCE_INPUTS) == {"source-one"}
      and set(MAPPING_INPUTS) == {"source-one"},
      "FROZEN_SOURCE_ONE_ONLY")
_rules_input = MAPPING_INPUTS["source-one"]
_stop(isinstance(_rules_input, list) and len(_rules_input) == 168,
      "168_CACHED_MAPPINGS_REQUIRED")
_source = SOURCE_INPUTS["source-one"].get("source_df")
_stop(_source is not None and hasattr(_source, "to_local_iterator"),
      "CACHED_SOURCE_DF_REQUIRED")

# Distinguish a temporary in-memory overlay from actual file-loaded Cell 7.
# Select ONLY the successful graph whose exact envelope matches this screenshot.
_possible = []
for _label, _gname, _rname in (
    ("OBJECT_OVERLAY_PREVIEW", "SSP_OBJECT_PREVIEW_GRAPHS",
     "SSP_OBJECT_PREVIEW_REPORT"),
    ("STANDARD_CELL7_PREVIEW", "MODEL_GRAPHS", "PIPELINE_REPORT"),
):
    _graphs0, _report0 = globals().get(_gname), globals().get(_rname)
    if not isinstance(_graphs0, dict) or not isinstance(_report0, dict):
        continue
    _groups0 = _report0.get("groups", [])
    if not (len(_groups0) == 1
            and (_groups0[0].get("source"), _groups0[0].get("model")) == _ROUTE
            and _ROUTE in _graphs0):
        continue
    _load0 = _groups0[0].get("load") or {}
    if (_report0.get("mode") == "PREVIEW"
            and _report0.get("status") == "PREVIEW_COMPLETE"
            and _report0.get("writes_executed") is False
            and _report0.get("commit_attempted") is False
            and _load0.get("mode") == "PREVIEW"
            and _load0.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
            and _load0.get("writes_executed") is False
            and _load0.get("committed") is False
            and _load0.get("persisted") is False
            and _load0.get("target_dml_attempted") is False
            and _load0.get("pre_write_validation_passed") is True
            and _load0.get("validation_passed") is True
            and _load0.get("storage_verified") is True
            and _load0.get("source_records") == 2813
            and _load0.get("nodes") == 879640
            and _load0.get("edges") == 876827
            and _load0.get("lineage_gaps") == 0
            and _load0.get("expected_changes", {}).get("D") == _EXPECTED_D
            and _load0.get("expected_changes", {}).get("F") == _EXPECTED_F):
        _possible.append((_label, _graphs0[_ROUTE], _report0, _groups0[0]))
_stop(bool(_possible), "NO_CACHED_PREVIEW_WITH_SCREENSHOT_COUNTS")
_fp_set = {
    x[1].get("context", {}).get("compiled_plan", {}).get("mapping_fingerprint")
    for x in _possible
}
_stop(len(_fp_set) == 1, "TWO_PREVIEW_GRAPHS_WITH_DIFFERENT_FINGERPRINTS")
_label, _graph, _report, _group = _possible[0]
_ctx = _graph.get("context") or {}
_plan = _ctx.get("compiled_plan") or {}
_fp = _plan.get("mapping_fingerprint")
_stop(isinstance(_fp, str) and len(_fp) == 64
      and _fp == _group.get("mapping_fingerprint"),
      "CANDIDATE_FINGERPRINT_DRIFT")
_stop(_ctx.get("config", {}).get("EXECUTE_WRITES") is False
      and _ctx.get("config", {}).get("OSCAL_MODEL") == "SSP",
      "CANDIDATE_CONTEXT_SCOPE")
_stop(_plan.get("release") == "lean-csv-registry-v17-cia-null-lineage",
      "UNEXPECTED_MAPPER_RELEASE")
# Actual Cell 3/4/5 parent identity rule, not a synthetic assumption:
# system-characteristics is an OBJECT with one "singleton" instance per
# source record; its property child has NO parent_instance_rule. Cell 4
# emits PARENT_INSTANCE_KEY=None, and Cell 5 legitimately resolves that
# child through the unique parent in this record and builds a real
# CONTAINS FACT edge. The edge, not equality of two instance-key strings,
# proves the stored parent-child relationship.
_elements = _plan.get("elements") or {}
_parent_spec = _elements.get(_PARENT, {})
_props_spec = _elements.get(_OWNER, {})
_parent_params = _parent_spec.get("parameters") or {}
_props_params = _props_spec.get("parameters") or {}
_stop(
    _parent_spec.get("operator") == "object"
    and _parent_params.get("registry_contract", {}).get("is_collection") is False
    and _props_spec.get("operator") == "properties"
    and _props_params.get("registry_contract", {}).get("parent_path") == _PARENT
    and "parent_instance_rule" not in _props_params,
    "UNEXPECTED_SINGLETON_PARENT_REGISTRY_CONTRACT",
)
_compiled = {
    r["SOURCE_FIELD_NAME"]: r
    for r in _ctx.get("mapping_rows", [])
    if r.get("SOURCE_FIELD_NAME") in _FIELDS
    and r.get("OWNER_ELEMENT_PATH") == _OWNER
}
_stop(set(_compiled) == set(_FIELDS), "SEVEN_COMPILED_FIELDS_NOT_FOUND")
_stop(all(_compiled[f]["TRANSFORM_ID"] == "json-text"
              and _compiled[f].get("REPRESENTATION") == "properties"
              and _compiled[f].get("REPRESENTATION_PARAMS", {}).get(
                  "preserve_null") is True for f in _FIELDS),
      "SEVEN_COMPILED_JSON_TEXT_NULL_RULES_DIFFERENT")
_raw_rules = {
    r["SOURCE_FIELD_NAME"]: r
    for r in _rules_input if r.get("SOURCE_FIELD_NAME") in _FIELDS
}
_stop(set(_raw_rules) == set(_FIELDS), "LOADED_SEVEN_FIELD_METADATA_MISSING")
_cache_modes = {r["TRANSFORM_ID"] for r in _raw_rules.values()}
_stop(_cache_modes in ({"direct"}, {"json-text"}),
      "MIXED_OR_UNREVIEWED_CACHED_TRANSFORMS")
_mode = ("CACHED_168_JSON_TEXT_RULES" if _cache_modes == {"json-text"}
         else "TEMPORARY_SEVEN_RULE_OVERLAY")
if _mode == "TEMPORARY_SEVEN_RULE_OVERLAY":
    _stop(_fp != _OLD_FP, "OLD_FINGERPRINT_WAS_NOT_REPLACED")

# Hash the actual currently staged Notebook Files CSV, when accessible.
# A temporary overlay may intentionally still have the older original file.
_blob_status = "NOT_ACCESSIBLE"
_profiles = [p for p in SOURCE_PROFILES if p.get("SOURCE_KEY") == "source-one"]
if len(_profiles) == 1:
    _file = _profiles[0].get("MAPPING_FILE")
    if isinstance(_file, str) and _file:
        try:
            with open(_file, "rb") as _stream:
                _bytes = _stream.read()
            _sha = hashlib.sha1(
                ("blob %d\0" % len(_bytes)).encode("ascii") + _bytes
            ).hexdigest()
            _blob_status = ("MATCHED_AUTHORITY_GIT_BLOB" if _sha == _GIT_CSV_BLOB
                            else "FILE_DIFFERS_FROM_CURRENT_GIT_CSV")
        except (OSError, IOError):
            _blob_status = "NOT_ACCESSIBLE"

# Original Archer selected source snapshot is immutable for this check.
# Keep values in memory only; output never contains source values or IDs.
_MISSING = object()
_raw = {}
_for_field = {f: Counter() for f in _FIELDS}
for _record in _source.to_local_iterator():
    _id = str(_record["SOURCE_RECORD_ID"])
    _stop(bool(_id) and _id not in _raw, "DUPLICATE_OR_BAD_SOURCE_RECORD")
    _doc = _metadata_parse(_record, _ctx)
    _current = {}
    for _f in _FIELDS:
        _value = resolve_json_path(_doc, _f, default=_MISSING)
        _current[_f] = _value
        if _value is _MISSING:
            _for_field[_f]["ABSENT"] += 1
        elif _value is None:
            _for_field[_f]["EXPLICIT_NULL"] += 1
        elif not _has_value(_value):
            _for_field[_f]["EMPTY_OMITTED"] += 1
        elif isinstance(_to_python(_value), dict):
            _for_field[_f]["OBJECT_VALUE"] += 1
        else:
            _for_field[_f]["OTHER_POPULATED_TYPE"] += 1
    _raw[_id] = _current
_stop(len(_raw) == 2813, "2813_SELECTED_RECORDS_MISMATCH")

# Choose at most 15 deterministic representative records, including rare
# null/absent/empty cases when present, plus evenly spaced records.
_ids = sorted(_raw)
_sample = []
for _f in _FIELDS:
    for _kind in ("EXPLICIT_NULL", "ABSENT", "EMPTY_OMITTED"):
        if len(_sample) >= 15:
            break
        for _id in _ids:
            _v = _raw[_id][_f]
            _found = ((_kind == "ABSENT" and _v is _MISSING)
                      or (_kind == "EXPLICIT_NULL" and _v is None)
                      or (_kind == "EMPTY_OMITTED" and _v is not _MISSING
                          and _v is not None and not _has_value(_v)))
            if _found and _id not in _sample:
                _sample.append(_id)
                break
for _i in range(15):
    _id = _ids[(_i * (len(_ids) - 1)) // 14]
    if _id not in _sample and len(_sample) < 15:
        _sample.append(_id)
_stop(0 < len(_sample) <= 15, "EMPTY_SAMPLE")

_nodes = _graph.get("nodes")
_edges = _graph.get("edges")
_stop(_nodes is not None and _edges is not None, "CACHED_GRAPH_MISSING")
_selected_prop = _nodes.filter(
    (_oscal_col("ELEMENT_PATH") == _OWNER)
    & _oscal_col("SOURCE_RECORD_ID").isin(*_sample)
).select("SOURCE_RECORD_ID", "NODE_KEY", "METADATA_JSON",
         "PARENT_NODE_PATH", "PARENT_INSTANCE_KEY")
_selected_parents = _nodes.filter(
    (_oscal_col("ELEMENT_PATH") == _PARENT)
    & _oscal_col("SOURCE_RECORD_ID").isin(*_sample)
).select("SOURCE_RECORD_ID", "NODE_KEY", "INSTANCE_KEY")
_parent = {}
for _n in _selected_parents.to_local_iterator():
    _id = str(_n["SOURCE_RECORD_ID"])
    _stop(_id not in _parent, "DUPLICATED_SYSTEM_CHARACTERISTICS_PARENT")
    _parent[_id] = (str(_n["NODE_KEY"]), str(_n["INSTANCE_KEY"]))
_stop(set(_parent) == set(_sample),
      "SYSTEM_CHARACTERISTICS_PARENT_NOT_FOUND")

_props = {}
_prop_keys = {}
_valid_names = {_stable_property_name(f) for f in _FIELDS}
for _n in _selected_prop.to_local_iterator():
    _meta = _to_python(_n["METADATA_JSON"])
    if isinstance(_meta, str):
        _meta = json.loads(_meta)
    _stop(isinstance(_meta, dict), "INVALID_METADATA_JSON_OBJECT")
    _name = _meta.get("name")
    if _name not in _valid_names:
        continue
    _id = str(_n["SOURCE_RECORD_ID"])
    _key = (_id, _name)
    _stop(_key not in _props, "DUPLICATE_FIELD_ON_SAMPLED_RECORD")
    _props[_key] = _meta.get("value", _MISSING)
    _nodekey = str(_n["NODE_KEY"])
    _stop(
        _n["PARENT_NODE_PATH"] == _PARENT
        and _parent[_id][1] == "singleton"
        and _n["PARENT_INSTANCE_KEY"] is None,
        "WRONG_PROPERTY_PARENT_INSTANCE",
    )
    # The actual materialized FACT CONTAINS edge to this record's exact
    # parent NODE_KEY is independently checked in the next section.
    _prop_keys[_nodekey] = _id

# Verify each sampled property's unique real CONTAINS FACT edge and parent.
_seen_edges = Counter()
if _prop_keys:
    _edge_rows = _edges.filter(
        _oscal_col("FK_TARGET_ELEMENT_HASH").isin(*list(_prop_keys))
    ).select("FK_SOURCE_ELEMENT_HASH", "FK_TARGET_ELEMENT_HASH",
             "DEPENDENCY_TYPE")
    for _e in _edge_rows.to_local_iterator():
        _target = str(_e["FK_TARGET_ELEMENT_HASH"])
        _stop(_target in _prop_keys, "UNREQUESTED_FACT_EDGE")
        _id = _prop_keys[_target]
        _stop(_e["DEPENDENCY_TYPE"] == "CONTAINS"
              and str(_e["FK_SOURCE_ELEMENT_HASH"]) == _parent[_id][0],
              "PROPERTY_FACT_WRONG_PARENT_OR_RELATIONSHIP")
        _seen_edges[_target] += 1
    _stop(all(_seen_edges[k] == 1 for k in _prop_keys),
          "PROPERTY_FACT_MISSING_OR_DUPLICATED")

_mismatch = Counter()
_match = Counter()
for _id in _sample:
    for _f in _FIELDS:
        _name = _stable_property_name(_f)
        _raw_value = _raw[_id][_f]
        _actual = _props.get((_id, _name), _MISSING)
        if _raw_value is _MISSING or (
                _raw_value is not None and not _has_value(_raw_value)):
            if _actual is _MISSING:
                _match[_f] += 1
            else:
                _mismatch[_f] += 1
        elif _raw_value is None:
            if _actual is None:
                _match[_f] += 1
            else:
                _mismatch[_f] += 1
        else:
            try:
                _expected = json.dumps(
                    _to_python(_raw_value), sort_keys=True,
                    separators=(",", ":"), allow_nan=False
                )
            except (TypeError, ValueError):
                _mismatch[_f] += 1
                continue
            if _actual == _expected:
                _match[_f] += 1
            else:
                _mismatch[_f] += 1

print("SOURCE_ONE_SSP_168_SEVEN_OBJECT_PREVIEW_VALUE_QA_READ_ONLY")
print("PREVIEW_VARIABLE_SOURCE:", _label)
print("PREVIEW_MAPPING_FINGERPRINT:", _fp)
print("MAPPING_INPUT_SCOPE:", _mode)
print("NOTEBOOK_FILES_CSV_BLOB:", _blob_status)
print("SOURCE_RECORDS:", len(_raw))
print("SAMPLED_RECORDS:", len(_sample))
print("EXPECTED_DIM_INSERTS:", _EXPECTED_D["INSERTS"])
print("EXPECTED_FACT_INSERTS:", _EXPECTED_F["INSERTS"])
print("SAMPLED_PROPERTY_PARENT_FACT_EDGES_VERIFIED:", len(_prop_keys))
for _f in _FIELDS:
    _counts = dict(_for_field[_f])
    print("FIELD_QA:", _f,
          "SOURCE_OBJECT=", _counts.get("OBJECT_VALUE", 0),
          "SOURCE_NULL=", _counts.get("EXPLICIT_NULL", 0),
          "SOURCE_ABSENT=", _counts.get("ABSENT", 0),
          "SOURCE_EMPTY=", _counts.get("EMPTY_OMITTED", 0),
          "SOURCE_OTHER_POPULATED=", _counts.get("OTHER_POPULATED_TYPE", 0),
          "SAMPLE_MATCH=", _match[_f],
          "SAMPLE_MISMATCH=", _mismatch[_f])
print("SAMPLED_FIELD_VALUE_MISMATCHES:", sum(_mismatch.values()))
_result = ("PASS_SAMPLED_SEVEN_FIELDS_SOURCE_TO_GRAPH_AND_PARENT_FACT"
           if sum(_mismatch.values()) == 0
           else "REVIEW_REQUIRED_FIELD_VALUE_MISMATCHES")
print("RESULT:", _result)
print("NO TARGET DIM/FACT WRITES, NO COMMIT, NO SOURCE VALUES OR CONTENT IDS.")
if _mismatch:
    raise RuntimeError("SSP_SEVEN_OBJECT_PARITY_STOP_MISMATCHES_REVIEW_REQUIRED")
