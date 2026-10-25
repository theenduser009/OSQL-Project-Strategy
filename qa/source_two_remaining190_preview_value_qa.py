# Source Two six-field190 release audit: retained PREVIEW only.
# Tests six additions plus two existing same-name scope counterparts.
# No mapper/loader calls, RAW/target queries, approval changes or writes.
# Each retained source/owner frame and Catalog nodes/edges is traversed once.
import hashlib
import json
import re
from collections import Counter, defaultdict

# Filled from independently compiled private cloud release, never the live session.
PINNED_FINGERPRINTS = {
    "source-two-source/CATALOG": "e51e4df15419600adc6607dd3c446c394f314e3381c776b33db13c68a5d2bf99",
    "source-two-topic/ASSESSMENT_RESULTS": "81b779d3d32f69d06624e542d0ab3eea6e4f7d4e8c773e983fae7a7dfb66157f",
    "source-two-section/ASSESSMENT_RESULTS": "ed61b12a23f6fd44a1058046be937aedd52adc90b4d85c3651f992f97a56d0b1",
    "source-two-subsection/ASSESSMENT_RESULTS": "ff6d5b90751253ec896490a1c580f5f3b6181e2929a078818d1b1f2afeb8c97f"
}

_SCOPE = "COMPLIANCE_ENGAGEMENTS_SCOPE_PROCEDURES_FROM_SELECTED_AUTHORITATIVE_SOURCES"
_M = "catalog.metadata.props[]"
_T = "catalog.groups[]"
_S = "catalog.groups[].groups[]"
_U = "catalog.groups[].groups[].groups[]"
# field, owner, lookup, property_name, new_addition
SPECS = (
    (_SCOPE, _T, "topics", "compliance-engagements-scope-procedures-from-selected-authoritative-sources", True),
    (_SCOPE, _U, "subsections", "compliance-engagements-scope-procedures-from-selected-authoritative-sources", True),
    ("CONTROL_PROCEDURES_SELECTED_AUTHORITATIVE_SOURCE_SUB_SECTIONS", _U, "subsections", "control-procedures-selected-authoritative-source-sub-sections", True),
    ("CONTROL_STANDARDS_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS", _M, None, "control-standards-from-topic-section-and-subsection-levels", True),
    ("CONTROL_STANDARDS_FROM_SECTION_AND_SUBSECTION_LEVELS", _T, "topics", "control-standards-from-section-and-subsection-levels", True),
    ("CONTROL_STANDARDS_FROM_SECTION_LEVEL_AND_BELOW", _S, "sections", "control-standards-from-section-level-and-below", True),
    (_SCOPE, _M, None, "compliance-engagements-scope-procedures-from-selected-authoritative-sources", False),
    (_SCOPE, _S, "sections", "compliance-engagements-scope-procedures-from-selected-authoritative-sources", False),
)
ROUTES = {
    ("source-two-source", "CATALOG"): 157,
    ("source-two-topic", "ASSESSMENT_RESULTS"): 7,
    ("source-two-section", "ASSESSMENT_RESULTS"): 10,
    ("source-two-subsection", "ASSESSMENT_RESULTS"): 16,
}
_ERRORS = ("missing_values", "unexpected_values", "invalid_property_shape",
           "wrong_owner_occurrences", "orphan_property_values", "ownership_errors")


def _require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def _rows(frame):
    _require(callable(getattr(frame, "to_local_iterator", None)),
             "QA_RETAINED_FRAME_REQUIRED")
    for row in frame.to_local_iterator():
        yield row.as_dict(recursive=True) if hasattr(row, "as_dict") else dict(row)


def _object(value, context=None):
    if value is None and context is not None and context["compiled_plan"].get("options", {}).get("null_source_as_empty"):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            raise RuntimeError("QA_RETAINED_JSON_OBJECT_INVALID") from None
    _require(isinstance(value, dict), "QA_RETAINED_JSON_OBJECT_REQUIRED")
    return value


def _identity(value):
    _require(value is not None and str(value).strip(), "QA_RETAINED_ID_REQUIRED")
    return str(value).strip()


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expected(value):
    if value is None or value == "" or value == [] or value == {}:
        return Counter()
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        raise RuntimeError("QA_RAW_JSON_NOT_SERIALIZABLE") from None
    return Counter({_digest(text): 1})


def _fingerprint(context):
    plan, rows = context["compiled_plan"], context["mapping_rows"]
    _require(isinstance(rows, list) and plan.get("mappings") == rows,
             "QA_COMPILED_ROWS_CHANGED")
    value = rows
    native = plan.get("native_catalog")
    if native and native.get("guid_props"):
        value = {"mappings": rows, "guid_props": native["guid_props"]}
    for key in ("owner_procedure_props", "scalar_array_properties"):
        if plan.get(key) is not None:
            value = {"baseline": value, key: plan[key]}
    digest = _digest(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")))
    _require(plan.get("mapping_fingerprint") == digest, "QA_COMPILED_FINGERPRINT_CHANGED")
    return digest


def run_source_two_remaining190_value_qa(model_graphs, source_inputs, pipeline_report, progress=None):
    """Counts-only value/owner audit; hashes are retained in memory, never printed."""
    _require(progress is None or callable(progress), "QA_PROGRESS_CALLBACK_REQUIRED")
    def phase(name):
        if progress:
            progress(name)
    _require(isinstance(PINNED_FINGERPRINTS, dict) and set(PINNED_FINGERPRINTS) ==
             {"/".join(route) for route in ROUTES} and all(
                 isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                 for value in PINNED_FINGERPRINTS.values()),
             "QA_INDEPENDENT_RELEASE_PINS_REQUIRED")
    _require(isinstance(model_graphs, dict) and set(model_graphs) == set(ROUTES),
             "QA_EXACT_FOUR_ROUTES_REQUIRED")
    _require(isinstance(source_inputs, dict) and {route[0] for route in ROUTES}.issubset(source_inputs),
             "QA_FOUR_RETAINED_INPUTS_REQUIRED")
    _require(isinstance(pipeline_report, dict) and pipeline_report.get("mode") == "PREVIEW"
             and pipeline_report.get("status") == "PREVIEW_COMPLETE"
             and pipeline_report.get("writes_executed") is False
             and pipeline_report.get("commit_attempted") is False,
             "QA_SUCCESSFUL_NONWRITING_PREVIEW_REQUIRED")
    report_rows = pipeline_report.get("groups", [])
    _require(isinstance(report_rows, list) and len(report_rows) == 4
             and all(isinstance(row, dict) for row in report_rows),
             "QA_EXACT_FOUR_REPORT_GROUPS_REQUIRED")
    reports = {(row.get("source"), row.get("model")): row for row in report_rows}
    _require(set(reports) == set(ROUTES), "QA_EXACT_FOUR_REPORT_ROUTES_REQUIRED")
    for route, count in ROUTES.items():
        context = model_graphs[route]["context"]
        fingerprint = _fingerprint(context)
        load = reports[route]["load"]
        frozen = source_inputs[route[0]]
        _require(isinstance(frozen, dict) and callable(getattr(frozen.get("source_df"), "to_local_iterator", None))
                 and isinstance(frozen.get("selection"), dict)
                 and type(frozen["selection"].get("SELECTED_ROWS")) is int
                 and frozen["selection"]["SELECTED_ROWS"] >= 0
                 and frozen["selection"]["SELECTED_ROWS"] == load.get("source_records")
                 and context.get("source_key") == route[0]
                 and context["config"].get("OSCAL_MODEL") == route[1],
                 "QA_RETAINED_ROUTE_INPUT_OR_CONTEXT_MISMATCH")
        _require(fingerprint == PINNED_FINGERPRINTS["/".join(route)] ==
                 reports[route].get("mapping_fingerprint")
                 and context["routing_report"].get("STATUS") == "READY"
                 and context["routing_report"].get("SELECTED_ROWS") == count
                 and len(context["mapping_rows"]) == count
                 and context["config"].get("EXECUTE_WRITES") is False,
                 "QA_FIXED_RELEASE_OR_ROUTE_MISMATCH")
        _require(load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
                 and load.get("target_dml_attempted") is False
                 and load.get("writes_executed") is False,
                 "QA_SUCCESSFUL_NONWRITING_ROUTE_REQUIRED")
    route = ("source-two-source", "CATALOG")
    graph, source_input, load = model_graphs[route], source_inputs[route[0]], reports[route]["load"]
    context = graph["context"]
    _require(context["compiled_plan"].get("options", {}).get("parse_decimal") is False,
             "QA_APPROVED_JSON_NUMBER_POLICY_REQUIRED")
    rows = context["mapping_rows"]
    for field, owner, lookup, name, addition in SPECS:
        matches = [row for row in rows if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH")) == (field, owner)]
        _require(len(matches) == 1, "QA_EXACT_OWNER_FIELD_WRITER_REQUIRED")
        row = matches[0]
        target = owner if lookup is None else owner + ".props"
        params = {"property_name": name}
        if lookup is not None:
            params.update(target="props", joined_lookup=lookup)
        _require(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("CANONICAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else "props")
                 and row.get("REPRESENTATION") == ("properties" if lookup is None else "joined-records")
                 and row.get("TRANSFORM_ID") == "json-text"
                 and (row.get("VALUE_SOURCE") or "FIELD") == "FIELD"
                 and (row.get("NULL_POLICY") or "omit") == "omit"
                 and row.get("TRANSFORM_PARAMS") == {}
                 and row.get("REPRESENTATION_PARAMS") == params
                 and row.get("LINEAGE_REQUIRED_FLAG") is False,
                 "QA_EXACT_RAW_PROPERTY_CONTRACT_REQUIRED")
        _require(sum(other.get("OWNER_ELEMENT_PATH") == owner and
                     other.get("REPRESENTATION_PARAMS", {}).get("property_name") == name
                     for other in rows) == 1, "QA_DUPLICATE_PROPERTY_WRITER")
    phase("fixed-release-and-eight-owner-boundaries-verified")
    metrics = [Counter({key: 0 for key in (
        "source_records", "source_key_absent", "source_null_or_empty",
        "populated_source_records", "expected_values", "actual_values", "exact_records") + _ERRORS})
        for spec in SPECS]
    expected, original, source_ids = [dict() for spec in SPECS], {}, set()
    by_owner = defaultdict(list)
    for index, spec in enumerate(SPECS):
        by_owner[spec[1]].append(index)
    def retain(owner, identifier, root, parent_owner, parent_id, obj):
        key = (owner, root, identifier)
        _require(key not in original, "QA_DUPLICATE_FROZEN_OWNER")
        original[key] = (parent_owner, parent_id)
        for index in by_owner[owner]:
            field = SPECS[index][0]
            desired = _expected(obj.get(field))
            expected[index][(root, identifier)] = desired
            metric = metrics[index]
            metric["source_records"] += 1
            metric["source_key_absent"] += field not in obj
            metric["source_null_or_empty"] += field in obj and not desired
            metric["populated_source_records"] += bool(desired)
            metric["expected_values"] += sum(desired.values())
    for record in _rows(source_input["source_df"]):
        identifier = _identity(record["SOURCE_RECORD_ID"])
        _require(identifier not in source_ids, "QA_DUPLICATE_FROZEN_SOURCE")
        source_ids.add(identifier)
        retain(_M, identifier, identifier, "catalog", identifier,
               _object(record["CURATED_JSON"], context))
    _require(len(source_ids) == source_input["selection"]["SELECTED_ROWS"] ==
             load["source_records"] and bool(source_ids), "QA_SOURCE_COUNT_MISMATCH")
    joined = context.get("lookups", {}).get("joined_sources", {})
    contracts = context.get("lookups", {}).get("joined_contract", {})
    previous, previous_owner = {key: key for key in source_ids}, "catalog"
    for binding, owner in (("topics", _T), ("sections", _S), ("subsections", _U)):
        _require(binding in joined and isinstance(contracts.get(binding), dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_JOINED_OWNER_CONTRACT_REQUIRED")
        current = {}
        for record in _rows(joined[binding]):
            identifier, parent = _identity(record["_SOURCE_RECORD_ID"]), _identity(record["CONTENT_ID"])
            _require(identifier not in current and parent in previous, "QA_DUPLICATE_OR_UNROOTED_FROZEN_CHILD")
            root = previous[parent]
            current[identifier] = root
            retain(owner, identifier, root, previous_owner, parent,
                   _object(record["CURATED_JSON"], context))
        previous, previous_owner = current, owner
    phase("source-and-three-child-frames-compared-once")
    names = defaultdict(list)
    for index, spec in enumerate(SPECS):
        names[spec[3]].append(index)
    observed = [defaultdict(Counter) for spec in SPECS]
    summaries, owner_nodes = {}, defaultdict(list)
    table = context["config"]["SOURCE_TABLE_NAME"]
    source_prop_nodes = []
    group_paths = {_T, _S, _U}
    for node in _rows(graph["nodes"]):
        key, owner, root = node["NODE_KEY"], node["ELEMENT_PATH"], _identity(node["SOURCE_RECORD_ID"])
        _require(key not in summaries, "QA_DUPLICATE_GRAPH_NODE")
        payload = _object(node["METADATA_JSON"])
        props = payload.get("props", [])
        _require(isinstance(props, list), "QA_PROPERTIES_ARRAY_REQUIRED")
        identity = root
        if owner in group_paths:
            ids = [prop.get("value") for prop in props if isinstance(prop, dict)
                   and prop.get("name") == "archer-content-id"]
            identity = ids[0] if len(ids) == 1 and isinstance(ids[0], str) and ids[0] else None
        summaries[key] = (owner, root, node["SOURCE_TABLE_NAME"], identity)
        if owner in group_paths or owner in {"catalog", "catalog.metadata"}:
            _require(identity is not None, "QA_GROUP_PROVENANCE_REQUIRED")
            owner_nodes[(owner, root, identity)].append(key)
        located = [(payload, True, "props")]
        for member in ("props", "parts"):
            members = payload.get(member, [])
            _require(isinstance(members, list), "QA_NATIVE_MEMBERS_ARRAY_REQUIRED")
            located.extend((prop, False, member) for prop in members if isinstance(prop, dict))
        for prop, standalone, member in located:
            name, namespace = prop.get("name"), prop.get("ns")
            if name not in names or isinstance(namespace, str) and namespace.strip():
                continue
            matches = [index for index in names[name] if SPECS[index][1] == owner]
            if len(matches) != 1:
                for index in names[name]:
                    metrics[index]["wrong_owner_occurrences"] += 1
                continue
            index = matches[0]
            if standalone != (SPECS[index][2] is None) or member != "props":
                metrics[index]["wrong_owner_occurrences"] += 1
                continue
            metric = metrics[index]
            metric["ownership_errors"] += node["SOURCE_TABLE_NAME"] != table or identity is None
            valid = set(prop) == {"name", "value"} and isinstance(prop.get("value"), str)
            metric["invalid_property_shape"] += not valid
            if isinstance(prop.get("value"), str):
                observed[index][(root, identity)][_digest(prop["value"])] += 1
            if standalone:
                source_prop_nodes.append((index, key, root))
    parents = {}
    for edge in _rows(graph["edges"]):
        if edge["DEPENDENCY_TYPE"] != "CONTAINS":
            continue
        child, parent = edge["FK_TARGET_ELEMENT_HASH"], edge["FK_SOURCE_ELEMENT_HASH"]
        count, first = parents.get(child, (0, parent))
        parents[child] = (count + 1, first)
    def proper_parent(key, root, path, identifier):
        count, parent_key = parents.get(key, (0, None))
        parent = summaries.get(parent_key)
        return count == 1 and parent == (path, root, table, identifier)
    ownership_errors = 0
    for root in source_ids:
        roots = owner_nodes.pop(("catalog", root, root), [])
        metadata = owner_nodes.pop(("catalog.metadata", root, root), [])
        ownership_errors += len(roots) != 1 or any(summaries[key][2] != table for key in roots)
        ownership_errors += len(metadata) != 1
        ownership_errors += sum(not proper_parent(key, root, "catalog", root) for key in metadata)
    for (owner, root, identifier), (parent_owner, parent_id) in original.items():
        if owner == _M:
            continue
        keys = owner_nodes.pop((owner, root, identifier), [])
        ownership_errors += len(keys) != 1
        for key in keys:
            ownership_errors += summaries[key][2] != table
            ownership_errors += not proper_parent(key, root, parent_owner, parent_id)
    ownership_errors += sum(len(keys) for keys in owner_nodes.values())
    for index, key, root in source_prop_nodes:
        metrics[index]["ownership_errors"] += not proper_parent(key, root, "catalog.metadata", root)
    phase("catalog-nodes-and-edges-compared-once")
    for index, expected_records in enumerate(expected):
        metric = metrics[index]
        for key, desired in expected_records.items():
            actual = observed[index].pop(key, Counter())
            metric["actual_values"] += sum(actual.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += actual == desired
        metric["orphan_property_values"] += sum(sum(values.values()) for values in observed[index].values())
    error_count = ownership_errors + sum(metric[key] for metric in metrics for key in _ERRORS)
    return {
        "result": "PASS" if error_count == 0 else "REVIEW_REQUIRED",
        "error_count": error_count, "hierarchy_errors": ownership_errors,
        "new_field_occurrences": 6, "existing_same_name_counterparts": 2,
        "selected_rule_counts": {"/".join(route): count for route, count in ROUTES.items()},
        "fields": [dict(owner=spec[1], source_field=spec[0], new_addition=spec[4],
                        **dict(metrics[index])) for index, spec in enumerate(SPECS)],
        "scope": "Six new opaque values plus two existing same-name owner boundaries in retained190 PREVIEW. No persistence, native entities, links, aliases, full184 reaudit or Snowflake production claim.",
    }


_session = ("MODEL_GRAPHS", "SOURCE_INPUTS", "PIPELINE_REPORT")
if __name__ == "__main__" or any(name in globals() for name in _session):
    _require(all(name in globals() for name in _session), "QA_PREVIEW_SESSION_REQUIRED")
    SOURCE_TWO_REMAINING190_VALUE_QA = run_source_two_remaining190_value_qa(
        MODEL_GRAPHS, SOURCE_INPUTS, PIPELINE_REPORT,
        progress=lambda name: print("QA phase: " + name, flush=True))
    print("SOURCE_TWO_REMAINING190_PREVIEW_VALUE_QA")
    print(json.dumps(SOURCE_TWO_REMAINING190_VALUE_QA, indent=2))
    if SOURCE_TWO_REMAINING190_VALUE_QA["error_count"]:
        raise RuntimeError("QA_VALUE_OR_OWNERSHIP_REVIEW_REQUIRED")
