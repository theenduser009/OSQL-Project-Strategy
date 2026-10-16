# %% Source Two CATALOG — five-field PREVIEW parity and DIM change scope
# READ ONLY, 2026-10-16. Paste into ONE NEW Python cell in the EXISTING
# NB_ARCHER_OSCAL_MAPPER_V2 session AFTER the 31,982-update CATALOG PREVIEW.
# Reuses MODEL_GRAPHS / PIPELINE_REPORT / SOURCE_INPUTS, without rerunning Cells 1-7.
# Snowpark SELECTs only. NO DML, DDL, MERGE, registry change, or COMMIT.
# Prints only aggregate counts/field names, NEVER source values or Content IDs.

import json
from collections import Counter
from snowflake.snowpark import functions as F

_OSCAL_FIVE_ROUTE = ("source-two-source", "CATALOG")
_OSCAL_FIVE_PATHS = {
    "topics": ("catalog.groups[]", 1416, "catalog"),
    "sections": ("catalog.groups[].groups[]", 10566, "catalog.groups[]"),
    "subsections": ("catalog.groups[].groups[].groups[]", 20000,
                    "catalog.groups[].groups[]"),
}
_OSCAL_FIVE_FIELDS = {
    ("topics", "TOPIC_DATE_CREATED"): ("date-created", "timestamp"),
    ("topics", "TOPIC_LAST_UPDATED"): ("last-updated", "timestamp"),
    ("sections", "SUM_OF_SUB_SECTION_CRITICALITY_VALUE"):
        ("sub-section-criticality-sum", "direct"),
    ("subsections", "SUB_SECTION_DATE_CREATED"): ("date-created", "timestamp"),
    ("subsections", "SUB_SECTION_LAST_UPDATED"): ("last-updated", "timestamp"),
}
_OSCAL_FIVE_EXPECTED_D = {"INSERTS": 0, "UPDATES": 31982, "UNCHANGED": 1697}
_OSCAL_FIVE_EXPECTED_F = {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531}


def _oscal_five_require(condition, label):
    if not condition:
        raise RuntimeError("CATALOG_FIVE_FIELD_QA_BLOCKED_" + label)


def _oscal_five_doc(value):
    if hasattr(value, "as_dict"):
        value = value.as_dict(recursive=True)
    if isinstance(value, str):
        value = json.loads(value)
    _oscal_five_require(isinstance(value, dict), "INVALID_CACHED_JSON_OBJECT")
    return value


def run_oscal_five_field_preview_qa():
    env = globals()
    required = ("MODEL_GRAPHS", "PIPELINE_REPORT", "SOURCE_INPUTS",
                "_to_python", "resolve_json_path", "SKIP_VALUE",
                "_has_value", "_metadata_transform", "_oscal_property_values",
                "session")
    _oscal_five_require(all(name in env for name in required),
                        "MISSING_SAME_NOTEBOOK_PREVIEW_STATE")

    report = env["PIPELINE_REPORT"]
    graph_set = env["MODEL_GRAPHS"]
    route = _OSCAL_FIVE_ROUTE
    groups = report.get("groups", []) if isinstance(report, dict) else []
    _oscal_five_require(
        isinstance(graph_set, dict) and route in graph_set
        and report.get("mode") == "PREVIEW"
        and report.get("status") == "PREVIEW_COMPLETE"
        and report.get("writes_executed") is False
        and report.get("commit_attempted") is False
        and len(groups) == 1
        and (groups[0].get("source"), groups[0].get("model")) == route,
        "MATCHING_CATALOG_PREVIEW_REQUIRED",
    )
    load = groups[0].get("load") or {}
    _oscal_five_require(
        load.get("mode") == "PREVIEW"
        and load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
        and all(load.get(flag) is False for flag in
                ("writes_executed", "persisted", "committed",
                 "target_dml_attempted"))
        and all(load.get(flag) is True for flag in
                ("validation_passed", "pre_write_validation_passed",
                 "storage_verified"))
        and load.get("expected_changes", {}).get("D") == _OSCAL_FIVE_EXPECTED_D
        and load.get("expected_changes", {}).get("F") == _OSCAL_FIVE_EXPECTED_F
        and load.get("source_records") == 148
        and load.get("nodes") == 33679
        and load.get("edges") == 33531
        and load.get("lineage_gaps") == 0
        and all((load.get("approved_retirement") or {}).get(k) == 0
                for k in ("nodes", "edges", "source_records")),
        "PREVIEW_CHANGE_ENVELOPE_OR_VALIDATION_DRIFT",
    )

    graph = graph_set[route]
    ctx = graph.get("context") if isinstance(graph, dict) else None
    _oscal_five_require(isinstance(ctx, dict), "COMPILED_CONTEXT_MISSING")
    plan = ctx.get("compiled_plan") or {}
    rules = ctx.get("mapping_rows") or []
    _oscal_five_require(
        len(rules) == 57
        and ctx.get("config", {}).get("EXECUTE_WRITES") is False
        and plan.get("release") == "lean-csv-registry-v17-cia-null-lineage"
        and bool(plan.get("mapping_fingerprint"))
        and plan["mapping_fingerprint"] == groups[0].get("mapping_fingerprint"),
        "57_APPROVED_CATALOG_RULES_OR_FINGERPRINT_NOT_MATCHED",
    )
    selected = {}
    for (binding, field), (property_name, transform) in _OSCAL_FIVE_FIELDS.items():
        path = _OSCAL_FIVE_PATHS[binding][0]
        matching = [
            rule for rule in rules
            if rule.get("SOURCE_FIELD_NAME") == field
            and rule.get("OWNER_ELEMENT_PATH") == path
        ]
        _oscal_five_require(
            len(matching) == 1
            and matching[0].get("FIELD_RELATIVE_PATH") == "props"
            and matching[0].get("TRANSFORM_ID") == transform
            and matching[0].get("LOOKUP_KEY") == binding
            and (matching[0].get("REPRESENTATION_PARAMS") or {}).get(
                "property_name") == property_name,
            "FIELD_ROUTE_PROPERTY_OR_TRANSFORM_MISMATCH",
        )
        selected[(binding, field)] = matching[0]

    # Exact original Archer child identities come from _SOURCE_RECORD_ID,
    # NOT from joined frame CONTENT_ID (a parent-reference value).
    raw = {}
    projected = {}
    joined_frames = (env["SOURCE_INPUTS"].get("source-two-source") or {}
                     ).get("lookups", {}).get("joined_sources", {})
    joined_records = ctx.get("joined_record_lookups") or {}
    for binding, (_path, expected_count, _parent_path) in _OSCAL_FIVE_PATHS.items():
        frame = joined_frames.get(binding)
        joined = joined_records.get(binding)
        _oscal_five_require(
            frame is not None and hasattr(frame, "to_local_iterator")
            and isinstance(joined, dict),
            "FOUR_LEVEL_CACHED_SOURCE_FRAMES_MISSING",
        )
        fields = [field for (b, field) in _OSCAL_FIVE_FIELDS if b == binding]
        originals = {}
        for record in frame.to_local_iterator():
            child_id = str(record["_SOURCE_RECORD_ID"]).strip()
            _oscal_five_require(child_id and child_id not in originals,
                                "DUPLICATE_OR_MISSING_ARCHER_CHILD_ID")
            document = _oscal_five_doc(record["CURATED_JSON"])
            originals[child_id] = {
                field: env["resolve_json_path"](
                    document, field, default=env["SKIP_VALUE"])
                for field in fields
            }
        index = {}
        for root_id, children in joined.items():
            for child in children:
                child_id = str(child["source_record_id"]).strip()
                _oscal_five_require(child_id and child_id not in index,
                                    "DUPLICATE_PROJECTED_CHILD")
                index[child_id] = (str(root_id),
                                   child.get("parent_instance_key"))
        _oscal_five_require(
            len(originals) == expected_count
            and len(index) == expected_count
            and originals.keys() == index.keys(),
            "SOURCE_TO_PROJECTED_CHILD_COVERAGE",
        )
        raw[binding], projected[binding] = originals, index

    # Check each exact Catalog group node against the original child ID,
    # source root and parent reference. Do not print any identifiers.
    nodes = {binding: {} for binding in _OSCAL_FIVE_PATHS}
    by_path = {value[0]: key for key, value in _OSCAL_FIVE_PATHS.items()}
    total_nodes = 0
    for record in graph["nodes"].to_local_iterator():
        total_nodes += 1
        path = record["ELEMENT_PATH"]
        if path not in by_path:
            continue
        binding = by_path[path]
        metadata = _oscal_five_doc(record["METADATA_JSON"])
        props = metadata.get("props", [])
        _oscal_five_require(isinstance(props, list)
                            and all(isinstance(p, dict) and
                                    isinstance(p.get("name"), str)
                                    for p in props),
                            "INVALID_JOINED_GROUP_PROPS")
        ids = [p.get("value") for p in props
               if p["name"] == "archer-content-id"]
        _oscal_five_require(
            len(ids) == 1 and isinstance(ids[0], str)
            and ids[0] in raw[binding]
            and ids[0] not in nodes[binding],
            "GROUP_ARCHER_CONTENT_ID_PROVENANCE",
        )
        root_id, parent_key = projected[binding][ids[0]]
        _oscal_five_require(
            record["SOURCE_RECORD_ID"] == root_id
            and record["PARENT_NODE_PATH"] == _OSCAL_FIVE_PATHS[binding][2]
            and (binding == "topics"
                 or record["PARENT_INSTANCE_KEY"] == parent_key),
            "GROUP_SOURCE_OR_PARENT_RELATIONSHIP_MISMATCH",
        )
        nodes[binding][ids[0]] = props

    _oscal_five_require(
        total_nodes == 33679
        and all(len(nodes[binding]) == spec[1]
                for binding, spec in _OSCAL_FIVE_PATHS.items()),
        "JOINED_CANDIDATE_NODE_COVERAGE",
    )

    field_results = []
    for (binding, field), (property_name, transform) in _OSCAL_FIVE_FIELDS.items():
        counts = Counter()
        rule = selected[(binding, field)]
        for child_id, source_values in raw[binding].items():
            source_value = source_values[field]
            target = [p.get("value", env["SKIP_VALUE"])
                      for p in nodes[binding][child_id]
                      if p["name"] == property_name]
            if source_value is env["SKIP_VALUE"] or not env["_has_value"](source_value):
                if not target:
                    counts["source_empty_target_omitted"] += 1
                else:
                    counts["mismatches"] += 1
                continue
            counts["source_populated"] += 1
            try:
                converted = env["_metadata_transform"](rule, source_value, ctx)
                expected = env["_oscal_property_values"](converted)
                if len(expected) == 1 and target == expected:
                    counts["exact_transformed_value_matches"] += 1
                else:
                    counts["mismatches"] += 1
                if isinstance(source_value, str) and target != [source_value]:
                    counts["source_text_normalization_differences"] += 1
            except (ValueError, TypeError, ArithmeticError):
                counts["mismatches"] += 1
        field_results.append({
            "level": binding, "field": field, "property": property_name,
            "source_populated": counts["source_populated"],
            "exact_transformed_value_matches":
                counts["exact_transformed_value_matches"],
            "source_empty_target_omitted":
                counts["source_empty_target_omitted"],
            "mismatches": counts["mismatches"],
            "source_text_normalization_differences":
                counts["source_text_normalization_differences"],
        })

    # READ-ONLY Snowpark SELECT: compare the same PREVIEW candidate payloads
    # with the currently stored DIM. Reproduce loader VARIANT comparisons;
    # classify changed rows by their candidate element path.
    contract = ctx["config"].get("STORAGE_CONTRACT") or {}
    _oscal_five_require(
        contract.get("VERIFIED") is True
        and contract.get("MODEL_KEY") == "CATALOG",
        "CATALOG_DEV_TARGET_CONTRACT_NOT_VERIFIED",
    )
    stage = graph["nodes"].select(
        F.sql_expr("TO_BINARY(NODE_KEY, 'HEX')").alias("C_KEY"),
        F.col("ELEMENT_PATH").alias("OSCAL_PATH"),
        F.sql_expr("PARSE_JSON(METADATA_JSON)").alias("C_JSON"),
    )
    stored = env["session"].table(contract["TARGET_DIM"]).select(
        F.col(contract["DIM_PK_COLUMN"]).alias("T_KEY"),
        F.col("METADATA_JSON").alias("T_JSON"),
    )
    compared = stage.join(stored, stage["C_KEY"] == stored["T_KEY"], "left")
    missing_keys = compared.filter(F.col("T_KEY").is_null()).count()
    changed = compared.filter(F.sql_expr("C_JSON IS DISTINCT FROM T_JSON"))
    path_counts = {
        item["OSCAL_PATH"]: int(item["N"])
        for item in changed.group_by("OSCAL_PATH").agg(
            F.count(F.lit(1)).alias("N")).collect()
    }
    allowed_paths = {
        "catalog.groups[]": 1416,
        "catalog.groups[].groups[]": 10566,
        "catalog.groups[].groups[].groups[]": 20000,
    }
    value_errors = sum(x["mismatches"] for x in field_results)
    correct_coverage = all(
        x["source_populated"] ==
        _OSCAL_FIVE_PATHS[x["level"]][1]
        and x["source_empty_target_omitted"] == 0
        and x["exact_transformed_value_matches"] == x["source_populated"]
        for x in field_results
    )
    changed_path_pass = missing_keys == 0 and path_counts == allowed_paths
    result = {
        "status": "SOURCE_TWO_FIVE_FIELD_PRECOMMIT_READ_ONLY_QA",
        "writes_executed": False,
        "source_records": 148,
        "candidate_dim_nodes": total_nodes,
        "candidate_fact_edges": load["edges"],
        "selected_catalog_mapping_rules": len(rules),
        "mapping_fingerprint_matches_preview": True,
        "field_results": field_results,
        "field_mismatches_total": value_errors,
        "updated_path_counts": dict(sorted(path_counts.items())),
        "missing_dim_target_keys": missing_keys,
        "changed_path_gate": "PASS" if changed_path_pass else "BLOCKED",
        "result": (
            "PASS_FIVE_FIELD_VALUE_AND_CHANGED_PATH_QA"
            if value_errors == 0 and correct_coverage and changed_path_pass
            else "BLOCKED_REVIEW_BEFORE_COMMIT"
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["result"] != "PASS_FIVE_FIELD_VALUE_AND_CHANGED_PATH_QA":
        raise RuntimeError("CATALOG_FIVE_FIELD_QA_BLOCKED_REVIEW_COUNTS")
    return result


OSCAL_FIVE_FIELD_QA_REPORT = run_oscal_five_field_preview_qa()
