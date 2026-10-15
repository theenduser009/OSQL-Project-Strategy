# %% Source Two Topic/Section: four new Catalog properties vs original CURATED_JSON
# Date: 2026-10-15. READ ONLY. Run as ONE new Snowflake DEV notebook Python cell
# directly after the passing standalone NEXT_TOPIC_SECTION PREVIEW.
# Does not execute Cells 1-7, reload source, run SQL, or write DIM/FACT.
# Only aggregate counters appear: no Archer Content IDs or payload values.
import json
from collections import Counter

_ROUTE = ("source-two-source", "CATALOG")
_TOP_PATH = "catalog.groups[]"
_SEC_PATH = "catalog.groups[].groups[]"
_FIELDS = {
    ("topics", "DOCUMENT_NUMBER"): (_TOP_PATH, "document-number", "text"),
    ("topics", "TOTAL_NUMBER_OF_SECTIONS"): (_TOP_PATH, "section-count", "direct"),
    ("sections", "SECTION_SHORT_DESCRIPTION"): (_SEC_PATH, "short-description", "text"),
    ("sections", "TOTAL_NUMBER_OF_SUB_SECTIONS"): (_SEC_PATH, "sub-section-count", "direct"),
}
_DEFERRED_SECTION_FIELD = "INFORMATION"
_REQUIRED = (
    "NEXT_TOPIC_SECTION_GRAPHS", "NEXT_TOPIC_SECTION_REPORT",
    "SOURCE_INPUTS", "_to_python", "resolve_json_path",
    "_metadata_transform", "_oscal_property_values", "_has_value",
    "SKIP_VALUE",
)
_missing = [key for key in _REQUIRED if key not in globals()]
if _missing:
    raise RuntimeError("NEXT_FOUR_QA_MISSING_PREVIEW_OR_SOURCE_STATE: " +
                       ",".join(_missing))

def _check(condition, name):
    if not condition:
        raise RuntimeError("NEXT_FOUR_QA_BLOCKED_" + name)

_report = NEXT_TOPIC_SECTION_REPORT
_graphs = NEXT_TOPIC_SECTION_GRAPHS
_groups = _report.get("groups", []) if isinstance(_report, dict) else []
_check(
    isinstance(_graphs, dict) and _ROUTE in _graphs
    and isinstance(_report, dict)
    and _report.get("mode") == "PREVIEW"
    and _report.get("status") == "PREVIEW_COMPLETE"
    and _report.get("writes_executed") is False
    and _report.get("commit_attempted") is False
    and len(_groups) == 1
    and (_groups[0].get("source"), _groups[0].get("model")) == _ROUTE,
    "MATCHING_SOURCE_TWO_CATALOG_PREVIEW_ONLY"
)
_load = _groups[0].get("load") or {}
_expected_D = {"INSERTS": 0, "UPDATES": 11982, "UNCHANGED": 21697}
_expected_F = {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531}
_check(
    _load.get("mode") == "PREVIEW"
    and _load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
    and all(_load.get(k) is False for k in
            ("writes_executed", "committed", "persisted", "target_dml_attempted"))
    and all(_load.get(k) is True for k in
            ("pre_write_validation_passed", "validation_passed", "storage_verified"))
    and _load.get("expected_changes", {}).get("D") == _expected_D
    and _load.get("expected_changes", {}).get("F") == _expected_F
    and _load.get("nodes") == 33679
    and _load.get("edges") == 33531
    and _load.get("source_records") == 148
    and _load.get("lineage_gaps") == 0
    and all((_load.get("approved_retirement") or {}).get(k) == 0
            for k in ("nodes", "edges", "source_records")),
    "EXACT_PREVIEW_ENVELOPE_NO_TARGET_DML"
)

_graph = _graphs[_ROUTE]
_ctx = _graph.get("context") if isinstance(_graph, dict) else None
_check(isinstance(_ctx, dict), "COMPILED_CONTEXT_MISSING")
_plan = _ctx.get("compiled_plan") or {}
_rules = _ctx.get("mapping_rows") or []
_check(
    len(_rules) == 52
    and _ctx.get("config", {}).get("EXECUTE_WRITES") is False
    and _plan.get("release") == "lean-csv-registry-v17-cia-null-lineage"
    and bool(_plan.get("mapping_fingerprint"))
    and _plan["mapping_fingerprint"] == _groups[0].get("mapping_fingerprint"),
    "FIFTY_TWO_CATALOG_RULES_AND_FINGERPRINT"
)

_selected = {}
for (binding, field), (path, property_name, transform) in _FIELDS.items():
    matched = [r for r in _rules
               if r.get("OWNER_ELEMENT_PATH") == path
               and r.get("SOURCE_FIELD_NAME") == field]
    _check(
        len(matched) == 1
        and matched[0].get("TRANSFORM_ID") == transform
        and matched[0].get("FIELD_RELATIVE_PATH") == "props"
        and matched[0].get("REPRESENTATION_PARAMS", {}).get("property_name") == property_name
        and matched[0].get("LOOKUP_KEY") == binding,
        "EXACT_NEW_FIELD_PATH_OR_TRANSFORM"
    )
    _selected[(binding, field)] = matched[0]
_check(not any(r.get("OWNER_ELEMENT_PATH") == _SEC_PATH
               and r.get("SOURCE_FIELD_NAME") == _DEFERRED_SECTION_FIELD
               for r in _rules), "DEFERRED_SECTION_INFORMATION_ACTIVE")

# IMPORTANT: the joined frame's CONTENT_ID is a parent reference.
# _SOURCE_RECORD_ID is the original child Archer Content ID. Map the
# candidate native archer-content-id prop to that original child ID.
_raw_sources = {}
_projected_by_binding = {}
for _binding, _expected_count in (("topics", 1416), ("sections", 10566)):
    _frame = SOURCE_INPUTS.get("source-two-source", {}).get(
        "lookups", {}).get("joined_sources", {}).get(_binding)
    _joined = _ctx.get("joined_record_lookups", {}).get(_binding)
    _check(_frame is not None and isinstance(_joined, dict),
           "ORIGINAL_CHILD_LOOKUP_UNAVAILABLE")
    _original = {}
    for _row in _frame.to_local_iterator():
        _child_id = str(_row["_SOURCE_RECORD_ID"]).strip()
        _doc = _to_python(_row["CURATED_JSON"])
        if isinstance(_doc, str):
            _doc = json.loads(_doc)
        _check(isinstance(_doc, dict) and bool(_child_id)
               and _child_id not in _original,
               "INVALID_OR_DUPLICATE_ORIGINAL_CHILD")
        _original[_child_id] = _doc
    _indexed = {}
    for _root, _children in _joined.items():
        for _child in _children:
            _child_id = str(_child["source_record_id"]).strip()
            _check(_child_id not in _indexed, "DUPLICATE_JOINED_CHILD")
            _indexed[_child_id] = (
                str(_root), _child.get("parent_instance_key"),
                _child["payload"]
            )
    _check(len(_original) == _expected_count and len(_indexed) == _expected_count
           and set(_original) == set(_indexed),
           "ORIGINAL_AND_PROJECTED_CHILD_INVENTORY_PARITY")
    _raw_sources[_binding] = _original
    _projected_by_binding[_binding] = _indexed

_nodes = {"topics": {}, "sections": {}}
_all_nodes = 0
for _row in _graph["nodes"].to_local_iterator():
    _all_nodes += 1
    _path = _row["ELEMENT_PATH"]
    if _path not in (_TOP_PATH, _SEC_PATH):
        continue
    _binding = "topics" if _path == _TOP_PATH else "sections"
    _meta = _to_python(_row["METADATA_JSON"])
    if isinstance(_meta, str):
        _meta = json.loads(_meta)
    _check(isinstance(_meta, dict), "INVALID_CANDIDATE_GROUP_METADATA")
    _props = _meta.get("props", [])
    _check(isinstance(_props, list)
           and all(isinstance(p, dict) and isinstance(p.get("name"), str)
                   for p in _props), "INVALID_GROUP_PROPERTIES")
    _ids = [p.get("value") for p in _props
            if p["name"] == "archer-content-id"]
    _check(len(_ids) == 1 and isinstance(_ids[0], str)
           and _ids[0] not in _nodes[_binding]
           and _ids[0] in _raw_sources[_binding],
           "CHILD_CONTENT_ID_PROVENANCE_MISSING_OR_DUPLICATED")
    _child_id = _ids[0]
    _root, _parent_key, _projected = _projected_by_binding[_binding][_child_id]
    _check(_row["SOURCE_RECORD_ID"] == _root
           and _row["PARENT_NODE_PATH"] ==
                ("catalog" if _binding == "topics" else _TOP_PATH),
           "CANDIDATE_WRONG_SOURCE_OR_PARENT_PATH")
    if _binding == "sections":
        _check(_row["PARENT_INSTANCE_KEY"] == _parent_key,
               "SECTION_PARENT_INSTANCE_IDENTITY_DIFFERENT")
        _check(not any(p["name"] == "information" for p in _meta.get("parts", [])),
               "DEFERRED_SECTION_INFORMATION_EMITTED")
    _nodes[_binding][_child_id] = _props

_check(_all_nodes == 33679
       and len(_nodes["topics"]) == 1416
       and len(_nodes["sections"]) == 10566,
       "CANDIDATE_GRAPH_NODE_COUNTS_CHANGED")

_counts = {key: Counter() for key in _FIELDS}
for (_binding, _field), (_path, _name, _transform) in _FIELDS.items():
    _rules_for_field = _selected[(_binding, _field)]
    for _child_id, _doc in _raw_sources[_binding].items():
        _counter = _counts[(_binding, _field)]
        _raw = resolve_json_path(_doc, _field, default=SKIP_VALUE)
        _stored = [p.get("value", SKIP_VALUE)
                   for p in _nodes[_binding][_child_id]
                   if p["name"] == _name]
        if _raw is SKIP_VALUE or not _has_value(_raw):
            if not _stored:
                _counter["SOURCE_EMPTY_TARGET_OMITTED"] += 1
            else:
                _counter["MISMATCHES"] += 1
            continue
        _counter["SOURCE_POPULATED"] += 1
        try:
            _mapped = _metadata_transform(_rules_for_field, _raw, _ctx)
            _values = _oscal_property_values(_mapped)
            if len(_values) != 1:
                _counter["MISMATCHES"] += 1
                continue
            if _stored == [_values[0]]:
                _counter["EXACT_TRANSFORMED_VALUE_MATCHES"] += 1
            else:
                _counter["MISMATCHES"] += 1
            if _transform == "text" and _stored != [_raw]:
                _counter["RAW_TEXT_SPACING_DIFFERENCES"] += 1
        except (ValueError, TypeError, ArithmeticError):
            _counter["MISMATCHES"] += 1

_doc = _counts[("topics", "DOCUMENT_NUMBER")]
_check(_doc["SOURCE_POPULATED"] == 13
       and _doc["SOURCE_EMPTY_TARGET_OMITTED"] == 1403,
       "TOPIC_DOCUMENT_NUMBER_13_TEXT_1403_NULL_INVARIANT")

print("SOURCE_TWO_NEXT_FOUR_TOPIC_SECTION_ORIGINAL_RAW_FIELD_QA")
print("PREVIEW_SOURCE: NEXT_TOPIC_SECTION_STANDALONE")
print("TOPIC_ORIGINAL_AND_CANDIDATE_RECORDS:", len(_nodes["topics"]))
print("SECTION_ORIGINAL_AND_CANDIDATE_RECORDS:", len(_nodes["sections"]))
print("PREVIEW_DIM_UPDATES:", _expected_D["UPDATES"])
print("PREVIEW_FACT_INSERTS_UPDATES:", _expected_F["INSERTS"] + _expected_F["UPDATES"])
for _key in _FIELDS:
    _counts_here = _counts[_key]
    print(_key[0].upper() + "." + _key[1] + ":",
          json.dumps({
              "source_populated": _counts_here["SOURCE_POPULATED"],
              "exact_transformed_value_matches": _counts_here["EXACT_TRANSFORMED_VALUE_MATCHES"],
              "source_empty_target_omitted": _counts_here["SOURCE_EMPTY_TARGET_OMITTED"],
              "mismatches": _counts_here["MISMATCHES"],
              "raw_text_spacing_differences": _counts_here["RAW_TEXT_SPACING_DIFFERENCES"],
          }, sort_keys=True))
_total_mismatches = sum(r["MISMATCHES"] for r in _counts.values())
_raw_text_adjusted = sum(r["RAW_TEXT_SPACING_DIFFERENCES"] for r in _counts.values())
_state = ("PASS_FOUR_FIELD_SOURCE_TO_TRANSFORMED_TARGET_PARITY"
          if _total_mismatches == 0
          else "REVIEW_REQUIRED_FOUR_FIELD_TARGET_VALUE_PARITY")
print("FIELD_MISMATCHES_TOTAL:", _total_mismatches)
print("RAW_TEXT_SPACING_DIFFERENCES_DIAGNOSTIC:", _raw_text_adjusted)
print("RESULT:", _state)
print("No SQL, mapper/registry rerun, DIM/FACT target writes or COMMIT.")
if _total_mismatches:
    raise RuntimeError("Four-field source-to-OSCAL value differences require review")
