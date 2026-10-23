"""Inspect retained PREVIEW metadata; never query, rebuild, approve or write.

Run in a separate Python cell in the existing successful PREVIEW session.
The printed receipt contains runtime fingerprints, counts and destinations.
Keep that receipt private. A match is not approval or a new warehouse check.
An optional REVIEWED_PREVIEW_PROPOSAL dictionary can compare a saved proposal.
"""
import json
import re

_REVIEW_ROUTES = {("source-two-source", "CATALOG"): 126,
                  ("source-two-topic", "ASSESSMENT_RESULTS"): 7,
                  ("source-two-section", "ASSESSMENT_RESULTS"): 10,
                  ("source-two-subsection", "ASSESSMENT_RESULTS"): 16}

class _ReviewMetadataError(ValueError):
    pass

def _review_require(condition, code):
    if not condition:
        raise _ReviewMetadataError(code)

def _review_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_review_equal(left[k], right[k]) for k in left)
    return left == right

def _review_count(value):
    return type(value) is int and value >= 0

def _review_fingerprint(value):
    return (type(value) is str and re.fullmatch(r"[0-9a-fA-F]{64}", value)
            is not None and value != "0" * 64)

def _review_changes(value):
    return (type(value) is dict and set(value) == {"D", "F"} and all(
        type(value[kind]) is dict
        and set(value[kind]) == {"INSERTS", "UPDATES", "UNCHANGED"}
        and all(_review_count(n) for n in value[kind].values())
        for kind in ("D", "F")))

def _review_retirement(value):
    return (type(value) is dict and set(value) == {"nodes", "edges", "source_records"}
            and all(type(n) is int and n == 0 for n in value.values()))

def _review_route(group, graph):
    _review_require(type(group) is dict and type(graph) is dict, "ROUTE_METADATA_REQUIRED")
    source, model = group.get("source"), group.get("model")
    _review_require(type(source) is str and re.fullmatch(r"[a-z0-9-]+", source)
                    and type(model) is str and re.fullmatch(r"[A-Z_]+", model),
                    "ROUTE_IDENTITY_INVALID")
    ctx = graph.get("context")
    _review_require(type(ctx) is dict, "COMPILED_CONTEXT_REQUIRED")
    plan, config, routing = (ctx.get(k) for k in ("compiled_plan", "config", "routing_report"))
    _review_require(all(type(x) is dict for x in (plan, config, routing)),
                    "COMPILED_METADATA_REQUIRED")
    _review_require(ctx.get("source_key") == source and config.get("OSCAL_MODEL") == model,
                    "COMPILED_ROUTE_IDENTITY_MISMATCH")
    fingerprint = plan.get("mapping_fingerprint")
    _review_require(_review_fingerprint(fingerprint)
                    and fingerprint == group.get("mapping_fingerprint"),
                    "COMPILED_REPORT_FINGERPRINT_MISMATCH")
    rows, selected = ctx.get("mapping_rows"), routing.get("SELECTED_ROWS")
    _review_require(type(rows) is list and _review_count(selected) and selected > 0
                    and len(rows) == selected and routing.get("STATUS") == "READY",
                    "COMPILED_SELECTION_INVALID")
    _review_require(config.get("EXECUTE_WRITES") is False, "COMPILED_WRITE_MODE_NOT_FALSE")
    load = group.get("load")
    _review_require(type(load) is dict and load.get("mode") == "PREVIEW"
                    and load.get("model") == model
                    and load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML",
                    "SUCCESSFUL_ROUTE_PREVIEW_REQUIRED")
    _review_require(all(load.get(k) is False for k in
                    ("writes_executed", "persisted", "committed", "target_dml_attempted")),
                    "ROUTE_NO_WRITE_FLAGS_REQUIRED")
    _review_require(all(load.get(k) is True for k in
                    ("pre_write_validation_passed", "validation_passed", "storage_verified")),
                    "RETAINED_VALIDATION_FLAGS_REQUIRED")
    for metadata, key in ((load, "lineage_gaps"), (config, "LINEAGE_GAP_COUNT"),
                          (ctx.get("graph_report"), "LINEAGE_GAPS"),
                          (group.get("lineage"), "LINEAGE_GAPS")):
        _review_require(type(metadata) is dict and type(metadata.get(key)) is int
                        and metadata[key] == 0, "ZERO_LINEAGE_FLAGS_REQUIRED")
    changes, retired = load.get("expected_changes"), load.get("approved_retirement")
    _review_require(_review_changes(changes), "EXACT_CHANGE_COUNTS_REQUIRED")
    _review_require(_review_retirement(retired), "ZERO_RETIREMENT_COUNTS_REQUIRED")
    counts = {k: load.get(k) for k in ("nodes", "edges", "source_records")}
    _review_require(all(_review_count(n) for n in counts.values())
                    and counts["source_records"] > 0
                    and counts["nodes"] >= counts["source_records"]
                    and sum(changes["D"].values()) == counts["nodes"]
                    and sum(changes["F"].values()) == counts["edges"],
                    "CANDIDATE_COUNT_ARITHMETIC_MISMATCH")
    storage = config.get("STORAGE_CONTRACT")
    _review_require(type(storage) is dict and storage.get("VERIFIED") is True
                    and storage.get("MODEL_KEY") == model
                    and storage.get("PHYSICAL_PROFILE") == "BINARY16_UUID32",
                    "VERIFIED_STORAGE_METADATA_REQUIRED")
    destinations = {k: storage.get(k) for k in ("TARGET_DIM", "TARGET_FACT")}
    _review_require(all(type(v) is str and re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", v)
                    for v in destinations.values())
                    and destinations["TARGET_DIM"] != destinations["TARGET_FACT"],
                    "DESTINATION_METADATA_INVALID")
    storage_keys = ("SOURCE_SYSTEM_NAME", "SOURCE_TABLE_NAME", "RAW_TABLE", "IDENTITY_VERSION",
                    "ROOT_PATH", "ROOT_ELEMENT_TYPE", "DIM_PK_COLUMN", "FACT_PK_COLUMN")
    _review_require(all(type(storage.get(k)) is str and bool(storage[k].strip()) for k in storage_keys),
                    "STORAGE_BINDING_METADATA_REQUIRED")
    _review_require(all(config.get(k) == storage[k] for k in storage_keys[:6])
                    and all(config.get(k, storage[k]) == storage[k] for k in
                            ("TARGET_DIM", "TARGET_FACT", "DIM_PK_COLUMN", "FACT_PK_COLUMN")),
                    "COMPILED_STORAGE_BINDING_MISMATCH")
    _review_require(all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", storage[k])
                        for k in ("DIM_PK_COLUMN", "FACT_PK_COLUMN")), "STORAGE_KEY_METADATA_INVALID")
    return {"source": source, "model": model, "selected_rows": selected,
            "mapping_fingerprint": fingerprint,
            "expected_changes": {k: dict(v) for k, v in changes.items()},
            "approved_retirement": dict(retired), "candidate_counts": counts,
            "destinations": destinations,
            "storage_contract": {k: storage[k] for k in (*storage_keys, "MODEL_KEY",
                "VERIFIED", "PHYSICAL_PROFILE", "TARGET_DIM", "TARGET_FACT")}}

def review_retained_preview(model_graphs, pipeline_report, proposal=None, qa=None):
    """Return a new metadata receipt without touching frames or input state."""
    issues, current = [], []
    receipt = {"result": "REVIEW_REQUIRED_NO_WRITES", "issues": issues, "routes": current,
               "writes_performed": False, "commit_authorized": False,
               "qa_binding_verified": False, "qa_state": "QA_NOT_PRESENT_IN_GLOBALS",
               "validation_scope": "RETAINED_METADATA_ONLY_NO_NEW_DATA_READ_OR_VALIDATION"}
    if type(qa) is dict:
        if (qa.get("result") == "PASS" and type(qa.get("error_count")) is int
                and qa["error_count"] == 0):
            receipt["qa_state"] = "QA_PASS_PRESENT_UNBOUND"
            for section in ("scalar_array_properties", "native_information_criticality"):
                if type(qa.get(section)) is not dict or qa[section].get("status") != "CHECKED":
                    issues.append({"code": "QA_CURRENT_RELEASE_SECTION_NOT_CHECKED"})
        else:
            receipt["qa_state"] = "QA_PRESENT_REQUIRES_REVIEW"
            issues.append({"code": "QA_PASS_ZERO_ERRORS_REQUIRED"})
    elif qa is not None:
        issues.append({"code": "QA_METADATA_INVALID"})
    try:
        _review_require(type(model_graphs) is dict and type(pipeline_report) is dict,
                        "RETAINED_PREVIEW_SESSION_REQUIRED")
        _review_require(pipeline_report.get("mode") == "PREVIEW"
                        and pipeline_report.get("status") == "PREVIEW_COMPLETE"
                        and pipeline_report.get("writes_executed") is False
                        and pipeline_report.get("commit_attempted") is False,
                        "SUCCESSFUL_NO_WRITE_PREVIEW_REQUIRED")
        groups = pipeline_report.get("groups")
        _review_require(type(groups) is list and len(groups) == 4
                        and len(model_graphs) == 4, "EXACT_FOUR_ROUTES_REQUIRED")
        seen = set()
        for index, group in enumerate(groups):
            try:
                _review_require(type(group) is dict, "ROUTE_METADATA_REQUIRED")
                route = (group.get("source"), group.get("model"))
                _review_require(all(type(x) is str for x in route)
                                and route not in seen and route in model_graphs
                                and route in _REVIEW_ROUTES,
                                "DUPLICATE_OR_UNKNOWN_ROUTE")
                seen.add(route)
                current.append(_review_route(group, model_graphs[route]))
            except _ReviewMetadataError as error:
                issues.append({"route_index": index, "code": str(error)})
        _review_require(seen == set(model_graphs) == set(_REVIEW_ROUTES),
                        "EXACT_SOURCE_TWO_ROUTE_SET_REQUIRED")
        for index, row in enumerate(current):
            if row["selected_rows"] != _REVIEW_ROUTES[(row["source"], row["model"])]:
                issues.append({"route_index": index, "code": "CURRENT159_SELECTION_MISMATCH"})
        if proposal is not None:
            _review_require(type(proposal) is dict and type(proposal.get("routes")) is list
                            and len(proposal["routes"]) == 4, "REVIEWED_PROPOSAL_INVALID")
            expected = {}
            for row in proposal["routes"]:
                _review_require(type(row) is dict and type(row.get("source")) is str
                                and type(row.get("model")) is str, "REVIEWED_PROPOSAL_INVALID")
                key = (row["source"], row["model"])
                _review_require(key not in expected, "REVIEWED_PROPOSAL_DUPLICATE_ROUTE")
                _review_require(_review_count(row.get("selected_rows")) and row["selected_rows"] > 0
                                and _review_fingerprint(row.get("mapping_fingerprint"))
                                and _review_changes(row.get("expected_changes"))
                                and _review_retirement(row.get("approved_retirement"))
                                and type(row.get("candidate_counts")) is dict
                                and set(row["candidate_counts"]) == {"nodes", "edges", "source_records"}
                                and all(_review_count(n) for n in row["candidate_counts"].values())
                                and type(row.get("destinations")) is dict
                                and set(row["destinations"]) == {"TARGET_DIM", "TARGET_FACT"}
                                and all(type(v) is str for v in row["destinations"].values())
                                and type(row.get("storage_contract")) is dict,
                                "REVIEWED_PROPOSAL_INVALID")
                expected[key] = row
            _review_require(set(expected) == seen, "REVIEWED_PROPOSAL_ROUTE_SET_MISMATCH")
            for index, row in enumerate(current):
                old = expected[(row["source"], row["model"])]
                for key in ("selected_rows", "mapping_fingerprint", "expected_changes",
                            "approved_retirement", "candidate_counts", "destinations", "storage_contract"):
                    _review_require(key in old, "REVIEWED_PROPOSAL_INCOMPLETE")
                    if not _review_equal(old[key], row[key]):
                        issues.append({"route_index": index, "code": "REVIEWED_" + key.upper() + "_MISMATCH"})
        if not issues:
            receipt["result"] = ("MATCHED_REVIEWED_PREVIEW_NO_WRITES" if proposal is not None
                                 else "CAPTURED_REVIEW_REQUIRED_NO_WRITES")
    except _ReviewMetadataError as error:
        issues.append({"code": str(error)})
    except (ValueError, TypeError):
        issues.append({"code": "PREVIEW_METADATA_OR_PROPOSAL_REQUIRES_REVIEW"})
    return receipt

if __name__ == "__main__" or ("MODEL_GRAPHS" in globals() and "PIPELINE_REPORT" in globals()):
    print("RETAINED_PREVIEW_REVIEW_RECEIPT")
    print(json.dumps(review_retained_preview(
        globals().get("MODEL_GRAPHS"), globals().get("PIPELINE_REPORT"),
        globals().get("REVIEWED_PREVIEW_PROPOSAL"),
        globals().get("SOURCE_TWO_SCALAR_ARRAY159_VALUE_QA")), indent=2))
