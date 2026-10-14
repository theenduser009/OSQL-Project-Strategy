# %% Source Two: SIX NEW Sub-Section fields: original RAW -> PREVIEW payload
# 2026-10-14. Copy into ONE new Python cell immediately after the successful
# next-six PREVIEW cell, in the same Snowflake DEV notebook session.
# Read-only. No registry, DML, target-write loader call or mapper rerun.
# Accepts either standalone NEXT_* or Cell 7 MODEL_GRAPHS, only after
# verifying this exact six-field compiled mapping and no-write PREVIEW.
# Emits counts/statuses only: NO client payload text or Archer Content IDs.
import json
from collections import Counter

_route = ("source-two-source", "CATALOG")
_sub_path = "catalog.groups[].groups[].groups[]"
_section_path = "catalog.groups[].groups[]"
_active = {
    "SUB_SECTION_DESCRIPTION": ("parts", "overview", "text"),
    "SUB_SECTION_SHORT_DESCRIPTION": ("props", "short-description", "text"),
    "SUB_SECTION_MAPPING_STATUS": ("props", "mapping-status", "archer-select"),
    "NUMBER_OF_CONTROL_STANDARDS_SUB_SECTION_LEVEL": ("props", "control-count", "direct"),
    "COUNT_OF_CONTROLS": ("props", "total-controls", "direct"),
    "CONTENT_SOURCE": ("props", "content-source", "archer-select"),
}
_deferred = {
    "INFORMATION", "SUBSECTION_CRITICALITY_VALUE",
    "SUB_SECTION_DATE_CREATED", "SUB_SECTION_LAST_UPDATED",
}
# The standalone guarded preview saves NEXT_* names. A normal Cell 7
# PREVIEW saves the same graph under MODEL_GRAPHS / PIPELINE_REPORT instead.
# Validate the actual compiled SIX-field mapping before accepting either.
# Never alias an older accepted 52-row preview to the newer one blindly.
_need = (
    "SOURCE_INPUTS", "_metadata_transform", "_oscal_property_values",
    "_to_python", "resolve_json_path", "SKIP_VALUE", "_has_value",
)
_missing = [name for name in _need if name not in globals()]
if _missing:
    raise RuntimeError("NEXT_SIX_QA_REQUIRES_SOURCE_HELPERS: " +
                       ", ".join(_missing))

def _accepted_six_field_preview(graphs, report):
    if (not isinstance(graphs, dict) or not isinstance(report, dict)
            or report.get("mode") != "PREVIEW"
            or report.get("status") != "PREVIEW_COMPLETE"
            or report.get("writes_executed") is not False
            or report.get("commit_attempted") is not False
            or _route not in graphs):
        return False
    groups = report.get("groups", [])
    if (not isinstance(groups, list) or len(groups) != 1
            or (groups[0].get("source"), groups[0].get("model")) != _route):
        return False
    graph = graphs[_route]
    if not isinstance(graph, dict) or not isinstance(graph.get("context"), dict):
        return False
    ctx = graph["context"]
    rows = ctx.get("mapping_rows", [])
    sub_rows = [r for r in rows if r.get("OWNER_ELEMENT_PATH") == _sub_path]
    plan = ctx.get("compiled_plan") or {}
    load = groups[0].get("load") or {}
    return (
        len(rows) == 48 and len(sub_rows) == 10
        and _active.keys() <= {r.get("SOURCE_FIELD_NAME") for r in sub_rows}
        and not (_deferred & {r.get("SOURCE_FIELD_NAME") for r in sub_rows})
        and bool(plan.get("mapping_fingerprint"))
        and plan.get("mapping_fingerprint") == groups[0].get("mapping_fingerprint")
        and load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
        and load.get("writes_executed") is False
        and load.get("committed") is False
        and load.get("target_dml_attempted") is False
    )

_pair_options = (
    ("NEXT_SIX_STANDALONE", globals().get("NEXT_SOURCE_TWO_CATALOG_GRAPHS"),
     globals().get("NEXT_SOURCE_TWO_CATALOG_REPORT")),
    ("STANDARD_CELL_7", globals().get("MODEL_GRAPHS"),
     globals().get("PIPELINE_REPORT")),
)
_valid_pairs = [
    (label, graphs, report)
    for label, graphs, report in _pair_options
    if _accepted_six_field_preview(graphs, report)
]
if not _valid_pairs:
    raise RuntimeError(
        "NEXT_SIX_QA_NO_MATCHING_SIX_FIELD_PREVIEW_FOUND: "
        "expected a 48-rule CATALOG-only PREVIEW with the six new "
        "Sub-Section fields and a matching compiled fingerprint. "
        "Do not reuse the historical 52-row PREVIEW or rerun a prior COMMIT."
    )
if len(_valid_pairs) > 1:
    if (_valid_pairs[0][1] is not _valid_pairs[1][1]
            or _valid_pairs[0][2] is not _valid_pairs[1][2]):
        raise RuntimeError(
            "NEXT_SIX_QA_AMBIGUOUS_PREVIEW_STATE: both valid preview "
            "names refer to different objects. Review the latest candidate first."
        )
_qa_preview_source, _qa_graphs, _report = _valid_pairs[0]
_groups = _report["groups"]
print("SIX_FIELD_QA_PREVIEW_SOURCE:", _qa_preview_source)

_load = _groups[0].get("load", {})
_delta = _load.get("expected_changes", {})
_d, _f = _delta.get("D", {}), _delta.get("F", {})
if (any(_load.get(key) is not False for key in
        ("writes_executed", "committed", "persisted", "target_dml_attempted"))
        or _load.get("status") != "PREVIEW_PASSED_NO_TARGET_DML"
        or _load.get("mode") != "PREVIEW"
        or _load.get("nodes") != 33679
        or _load.get("edges") != 33531
        or _load.get("lineage_gaps") != 0
        or _load.get("pre_write_validation_passed") is not True
        or _load.get("validation_passed") is not True
        or _load.get("storage_verified") is not True
        or _load.get("source_records") != 148
        or _d.get("INSERTS") != 0
        or _d.get("UPDATES") != 20000
        or _d.get("UNCHANGED") != 13679
        or _f.get("INSERTS") != 0
        or _f.get("UPDATES") != 0
        or _f.get("UNCHANGED") != 33531):
    raise RuntimeError("NEXT_SIX_QA_PREVIEW_TARGET_DELTA_CHANGED")

_graph = _qa_graphs[_route]
_ctx = _graph["context"]
_rules = {r["SOURCE_FIELD_NAME"]: r for r in _ctx["mapping_rows"]
          if r["OWNER_ELEMENT_PATH"] == _sub_path}
if (len(_ctx["mapping_rows"]) != 48
        or len(_rules) != 10
        or set(_active) - set(_rules)
        or set(_rules) & _deferred
        or _ctx["config"].get("EXECUTE_WRITES") is not False
        or _groups[0].get("mapping_fingerprint") !=
           _ctx["compiled_plan"].get("mapping_fingerprint")):
    raise RuntimeError("NEXT_SIX_QA_COMPILED_MAPPING_MISMATCH")
for _field, (_member, _name, _transform) in _active.items():
    _r = _rules[_field]
    if (_r.get("FIELD_RELATIVE_PATH") != _member
            or _r.get("TRANSFORM_ID") != _transform
            or _r.get("REPRESENTATION_PARAMS", {}).get("property_name") != _name
            or _r.get("LOOKUP_KEY") != "subsections"):
        raise RuntimeError("NEXT_SIX_QA_MAPPING_PATH_OR_TRANSFORM_MISMATCH")

# The cached child CURATED_JSON frame is independent of projected joined
# field values. _SOURCE_RECORD_ID is the actual Archer child Content ID;
# CONTENT_ID on this joined frame is the Section parent reference.
_source = SOURCE_INPUTS.get("source-two-source", {})
_frame = _source.get("lookups", {}).get("joined_sources", {}).get("subsections")
_joined = _ctx.get("joined_record_lookups", {}).get("subsections")
if _frame is None or not isinstance(_joined, dict):
    raise RuntimeError("NEXT_SIX_QA_ORIGINAL_RAW_SNAPSHOT_NOT_AVAILABLE")

_original = {}
for _row in _frame.to_local_iterator():
    _cid = str(_row["_SOURCE_RECORD_ID"])
    _doc = _to_python(_row["CURATED_JSON"])
    if isinstance(_doc, str):
        _doc = json.loads(_doc)
    if (not isinstance(_doc, dict)
            or not _cid.strip() or _cid in _original):
        raise RuntimeError("NEXT_SIX_QA_BAD_OR_DUPLICATE_RAW_CONTENT_ID")
    _original[_cid] = _doc

_joined_by_id = {}
for _root_id, _children in _joined.items():
    for _child in _children:
        _cid = str(_child["source_record_id"])
        if _cid in _joined_by_id:
            raise RuntimeError("NEXT_SIX_QA_DUPLICATE_JOINED_CHILD")
        _joined_by_id[_cid] = (str(_root_id), _child["payload"])

if (len(_original) != 20000 or len(_joined_by_id) != 20000
        or set(_original) != set(_joined_by_id)):
    raise RuntimeError("NEXT_SIX_QA_SOURCE_INVENTORY_NOT_20000")

# Match the previewed Sub-Section node to the *original child Archer*
# Content ID preserved in a native named prop, NOT to the business group id.
_nodes = {}
_full_count = 0
for _n in _graph["nodes"].to_local_iterator():
    _full_count += 1
    if _n["ELEMENT_PATH"] != _sub_path:
        continue
    _meta = _to_python(_n["METADATA_JSON"])
    if isinstance(_meta, str):
        _meta = json.loads(_meta)
    if not isinstance(_meta, dict):
        raise RuntimeError("NEXT_SIX_QA_INVALID_SUBSECTION_JSON")
    _props = _meta.get("props", [])
    _parts = _meta.get("parts", [])
    if (not isinstance(_props, list) or not isinstance(_parts, list)
            or any(not isinstance(x, dict) or not isinstance(x.get("name"), str)
                   for x in _props + _parts)):
        raise RuntimeError("NEXT_SIX_QA_INVALID_PART_OR_PROP")
    if (any(p.get("name") in {"criticality-value", "date-created",
                              "last-updated"} for p in _props)
            or any(p.get("name") == "information" for p in _parts)):
        raise RuntimeError("NEXT_SIX_QA_DEFERRED_SUBSECTION_FIELD_EMITTED")
    _content_ids = [p.get("value") for p in _props
                    if p["name"] == "archer-content-id"]
    if (len(_content_ids) != 1
            or not isinstance(_content_ids[0], str)
            or _content_ids[0] in _nodes):
        raise RuntimeError("NEXT_SIX_QA_DUPLICATE_OR_MISSING_CONTENT_ID_PROP")
    _cid = _content_ids[0]
    _orig_identity = _original[_cid].get("SUB_SECTION_ID")
    if (_n["PARENT_NODE_PATH"] != _section_path
            or _cid not in _original
            or _n["SOURCE_RECORD_ID"] != _joined_by_id[_cid][0]
            or not isinstance(_orig_identity, str)
            or not _orig_identity.strip()
            or _n["INSTANCE_KEY"] != _orig_identity.strip()):
        raise RuntimeError("NEXT_SIX_QA_SUBSECTION_OWNER_OR_ID_MISMATCH")
    _nodes[_cid] = (_props, _parts)

if len(_nodes) != 20000 or _full_count != 33679:
    raise RuntimeError("NEXT_SIX_QA_INCOMPLETE_PREVIEW_NODES")

_counts = {field: Counter() for field in _active}
for _cid, _doc in _original.items():
    _props, _parts = _nodes[_cid]
    for _field, (_member, _name, _transform) in _active.items():
        _source_value = resolve_json_path(_doc, _field, default=SKIP_VALUE)
        _items = _parts if _member == "parts" else _props
        _stored = [x.get("prose" if _member == "parts" else "value",
                         SKIP_VALUE)
                   for x in _items if x["name"] == _name]
        _counter = _counts[_field]
        if _source_value is SKIP_VALUE or not _has_value(_source_value):
            if not _stored:
                _counter["SOURCE_EMPTY_TARGET_OMITTED"] += 1
            else:
                _counter["MISMATCHES"] += 1
            continue
        _counter["SOURCE_POPULATED"] += 1
        try:
            _mapped = _metadata_transform(_rules[_field], _source_value, _ctx)
            _values = _oscal_property_values(_mapped)
            if len(_values) != 1:
                _counter["MISMATCHES"] += 1
                continue
            _expected = _values[0]
            if _stored == [_expected]:
                _counter["EXACT_SOURCE_TO_OSCAL_MATCHES"] += 1
            else:
                _counter["MISMATCHES"] += 1
            if (_field == "SUB_SECTION_DESCRIPTION"
                    and _stored != [_source_value]):
                # Direct-prose source fidelity, independently of the generic
                # text transform's possible whitespace canonicalization.
                _counter["DIRECT_PROSE_DIFFERS_FROM_RAW"] += 1
        except (ValueError, TypeError, ArithmeticError):
            _counter["MISMATCHES"] += 1

print("SOURCE_TWO_NEXT_6_INDEPENDENT_CURATED_JSON_FIELD_QA")
print("ORIGINAL_SUBSECTION_RECORDS:", len(_original))
print("CANDIDATE_SUBSECTION_NODES:", len(_nodes))
print("PREVIEW_DIM_PAYLOAD_UPDATES:", _d["UPDATES"])
print("PREVIEW_FACT_INSERTS_OR_UPDATES:", _f["INSERTS"] + _f["UPDATES"])
for _field in sorted(_counts):
    _v = _counts[_field]
    print(_field + ":", json.dumps({
        "source_populated": _v["SOURCE_POPULATED"],
        "exact_source_to_oscal_matches": _v["EXACT_SOURCE_TO_OSCAL_MATCHES"],
        "source_empty_target_omitted": _v["SOURCE_EMPTY_TARGET_OMITTED"],
        "mismatches": _v["MISMATCHES"],
        "direct_prose_differs_from_raw": _v["DIRECT_PROSE_DIFFERS_FROM_RAW"],
    }, sort_keys=True))
_mismatch_total = sum(v["MISMATCHES"] for v in _counts.values())
_prose_delta = _counts["SUB_SECTION_DESCRIPTION"]["DIRECT_PROSE_DIFFERS_FROM_RAW"]
_result = ("PASS_EXACT_SIX_FIELD_SOURCE_PARITY"
           if _mismatch_total == 0 and _prose_delta == 0
           and _counts["SUB_SECTION_DESCRIPTION"]["SOURCE_POPULATED"] == 19962
           else "REVIEW_REQUIRED_EXACT_SIX_FIELD_SOURCE_PARITY")
print("FIELD_MISMATCHES_TOTAL:", _mismatch_total)
print("RAW_DIRECT_PROSE_DIFFERENCES:", _prose_delta)
print("RESULT:", _result)
print("No mapper rerun, registry SQL, target DIM/FACT DML, or COMMIT.")
if _result != "PASS_EXACT_SIX_FIELD_SOURCE_PARITY":
    raise RuntimeError("Review the six-field source-to-candidate parity before COMMIT")
