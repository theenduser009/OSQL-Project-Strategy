# %% Source Two Catalog: exact five NEW scalar mappings vs preview
# 2026-10-16. ONE new Snowflake Python cell, after 30,566-update PREVIEW.
# Reuses retained source and graph. Snowpark SELECT only; no DML/COMMIT.
# Prints field names and aggregate counts, never record IDs or values.

import json
from collections import Counter
from snowflake.snowpark import functions as F

route = ("source-two-source", "CATALOG")
expected_D = {"INSERTS": 0, "UPDATES": 30566, "UNCHANGED": 3113}
expected_F = {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531}
paths = {
    "sections": ("catalog.groups[].groups[]", 10566, "catalog.groups[]"),
    "subsections": ("catalog.groups[].groups[].groups[]", 20000, "catalog.groups[].groups[]"),
}
fields = [
    ("Source", "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_CONTENT_ID",
     "archer-content-id", "direct"),
    ("Source", "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_CONFIRMED_IN_ARCHER",
     "confirmed-date", "timestamp"),
    ("sections", "TOPIC_NAME", "topic", "text"),
    ("sections", "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_CONFIRMED_IN_ARCHER",
     "confirmed-date", "timestamp"),
    ("subsections", "TOPIC_NAME", "topic", "text"),
]


def _require(condition, code):
    if not condition:
        raise RuntimeError("CATALOG_NEW_FIVE_QA_BLOCKED_" + code)


def _obj(value):
    if hasattr(value, "as_dict"):
        value = value.as_dict(recursive=True)
    if isinstance(value, str):
        value = json.loads(value)
    _require(isinstance(value, dict), "INVALID_JSON_OBJECT")
    return value


def run_catalog_new_five_qa():
    globals_now = globals()
    for name in ("PIPELINE_REPORT", "MODEL_GRAPHS", "SOURCE_INPUTS",
                 "session", "resolve_json_path", "SKIP_VALUE",
                 "_has_value", "_metadata_transform", "_oscal_property_values"):
        _require(name in globals_now, "MISSING_PREVIEW_" + name)
    rep = PIPELINE_REPORT
    _require(rep.get("mode") == "PREVIEW"
             and rep.get("status") == "PREVIEW_COMPLETE"
             and rep.get("writes_executed") is False
             and rep.get("commit_attempted") is False
             and len(rep.get("groups", [])) == 1
             and (rep["groups"][0]["source"], rep["groups"][0]["model"]) == route
             and route in MODEL_GRAPHS, "PREVIEW_ROUTE")
    load = rep["groups"][0]["load"]
    _require(
        load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
        and load.get("expected_changes", {}).get("D") == expected_D
        and load.get("expected_changes", {}).get("F") == expected_F
        and load.get("nodes") == 33679 and load.get("edges") == 33531
        and load.get("source_records") == 148 and load.get("lineage_gaps") == 0
        and all(load.get(k) is True for k in
                ("pre_write_validation_passed", "validation_passed", "storage_verified"))
        and all(load.get(k) is False for k in
                ("writes_executed", "persisted", "committed", "target_dml_attempted"))
        and all((load.get("approved_retirement") or {}).get(k) == 0
                for k in ("nodes", "edges", "source_records")),
        "EXPECTED_30566_NO_WRITE_ENVELOPE")
    graph = MODEL_GRAPHS[route]
    ctx = graph["context"]
    rows = ctx["mapping_rows"]
    plan = ctx["compiled_plan"]
    _require(len(rows) == 62
             and ctx["config"].get("EXECUTE_WRITES") is False
             and plan.get("release") == "lean-csv-registry-v17-cia-null-lineage"
             and bool(plan.get("mapping_fingerprint"))
             and plan["mapping_fingerprint"] == rep["groups"][0]["mapping_fingerprint"],
             "62_RULES_AND_FINGERPRINT")
    mapped = {}
    for level, field, prop, transform in fields:
        owner = "catalog.metadata.props[]" if level == "Source" else paths[level][0]
        matching = [r for r in rows if r.get("SOURCE_FIELD_NAME") == field
                    and r.get("OWNER_ELEMENT_PATH") == owner]
        _require(len(matching) == 1 and matching[0].get("TRANSFORM_ID") == transform
                 and matching[0].get("FIELD_RELATIVE_PATH") ==
                    ("" if level == "Source" else "props")
                 and matching[0].get("LOOKUP_KEY") in
                    (("", None) if level == "Source" else (level,))
                 and (matching[0].get("REPRESENTATION_PARAMS") or {}).get(
                     "property_name") == prop, "EXACT_OWNER_FIELD_PROPERTY")
        mapped[(level, field)] = matching[0]

    inputs = SOURCE_INPUTS["source-two-source"]
    raw, owners = {}, {}
    root_df = inputs.get("source_df")
    _require(root_df is not None, "NO_SOURCE_CACHE")
    raw["Source"] = {}
    for r in root_df.to_local_iterator():
        source_id = str(r["SOURCE_RECORD_ID"]).strip()
        _require(source_id and source_id not in raw["Source"], "ROOT_ID_DUPLICATE")
        source_doc = _obj(r["CURATED_JSON"])
        raw["Source"][source_id] = {
            field: resolve_json_path(source_doc, field, default=SKIP_VALUE)
            for level, field, _, _ in fields if level == "Source"
        }
    _require(len(raw["Source"]) == 148, "ROOT_COUNT")

    for level, (path, count, parent_path) in paths.items():
        frame = (inputs.get("lookups") or {}).get("joined_sources", {}).get(level)
        joined = (ctx.get("joined_record_lookups") or {}).get(level)
        _require(frame is not None and isinstance(joined, dict),
                 "CHILD_FRAME_OR_LOOKUP_" + level)
        raw[level], owners[level] = {}, {}
        for r in frame.to_local_iterator():
            child_id = str(r["_SOURCE_RECORD_ID"]).strip()
            _require(child_id and child_id not in raw[level], "CHILD_ID_DUPLICATE")
            doc = _obj(r["CURATED_JSON"])
            raw[level][child_id] = {
                field: resolve_json_path(doc, field, default=SKIP_VALUE)
                for binding, field, _, _ in fields if binding == level
            }
        for root_id, children in joined.items():
            for child in children:
                child_id = str(child["source_record_id"]).strip()
                _require(child_id and child_id not in owners[level],
                         "CHILD_JOIN_DUPLICATE")
                owners[level][child_id] = (str(root_id), child.get("parent_instance_key"))
        _require(len(raw[level]) == count and len(owners[level]) == count
                 and raw[level].keys() == owners[level].keys(),
                 "CHILD_INVENTORY_" + level)

    # Source properties are separate DIM nodes; child properties are
    # embedded inside Section and Sub-Section group JSON payloads.
    root_props, child_props = {}, {level: {} for level in paths}
    by_path = {spec[0]: level for level, spec in paths.items()}
    seen_nodes = 0
    root_names = {prop for level, _, prop, _ in fields if level == "Source"}
    for r in graph["nodes"].to_local_iterator():
        seen_nodes += 1
        path = r["ELEMENT_PATH"]
        if path == "catalog.metadata.props[]":
            data = _obj(r["METADATA_JSON"])
            if data.get("name") in root_names:
                source_id = r["SOURCE_RECORD_ID"]
                _require(source_id in raw["Source"], "SOURCE_PROP_ROOT")
                bucket = root_props.setdefault(source_id, {})
                name = data["name"]
                _require(name not in bucket, "DUPLICATE_SOURCE_PROP")
                bucket[name] = data.get("value", SKIP_VALUE)
        elif path in by_path:
            level = by_path[path]
            data = _obj(r["METADATA_JSON"])
            props = data.get("props", [])
            _require(isinstance(props, list) and
                     all(isinstance(p, dict) and isinstance(p.get("name"), str)
                         for p in props), "INVALID_GROUP_PROPS")
            ids = [p.get("value") for p in props if p["name"] == "archer-content-id"]
            _require(len(ids) == 1 and isinstance(ids[0], str)
                     and ids[0] in raw[level]
                     and ids[0] not in child_props[level], "ORIGINAL_CHILD_ID")
            root, parent = owners[level][ids[0]]
            _require(r["SOURCE_RECORD_ID"] == root
                     and r["PARENT_NODE_PATH"] == paths[level][2]
                     and r["PARENT_INSTANCE_KEY"] == parent,
                     "GROUP_OWNER_RELATIONSHIP")
            child_props[level][ids[0]] = props
    _require(seen_nodes == 33679
             and all(len(child_props[level]) == spec[1]
                     for level, spec in paths.items()),
             "GRAPH_CHILD_NODE_COUNTS")

    results = []
    source_id_differences = 0
    for level, field, prop, transform in fields:
        counts = Counter()
        for child_id, original in raw[level].items():
            value = original[field]
            if level == "Source":
                saved = root_props.get(child_id, {}).get(prop, SKIP_VALUE)
                stored_values = [] if saved is SKIP_VALUE else [saved]
            else:
                stored_values = [
                    p.get("value", SKIP_VALUE) for p in child_props[level][child_id]
                    if p["name"] == prop
                ]
            if value is SKIP_VALUE or not _has_value(value):
                counts["source_empty_target_omitted" if not stored_values
                       else "mismatches"] += 1
                continue
            counts["source_populated"] += 1
            try:
                transformed = _metadata_transform(mapped[(level, field)], value, ctx)
                expected = _oscal_property_values(transformed)
                if len(expected) == 1 and stored_values == expected:
                    counts["exact_value_matches"] += 1
                else:
                    counts["mismatches"] += 1
                if field.endswith("SOURCE_CONTENT_ID") and str(value).strip() != child_id:
                    source_id_differences += 1
            except (TypeError, ValueError, ArithmeticError):
                counts["mismatches"] += 1
        results.append({
            "level": level, "field": field, "property": prop,
            "records_checked": len(raw[level]),
            **{name: counts[name] for name in
               ("source_populated", "exact_value_matches",
                "source_empty_target_omitted", "mismatches")},
        })

    contract = ctx["config"].get("STORAGE_CONTRACT") or {}
    _require(contract.get("VERIFIED") is True
             and contract.get("MODEL_KEY") == "CATALOG",
             "VERIFIED_CATALOG_STORAGE_CONTRACT")
    candidate = graph["nodes"].select(
        F.sql_expr("TO_BINARY(NODE_KEY, 'HEX')").alias("C_KEY"),
        F.col("ELEMENT_PATH").alias("OSCAL_PATH"),
        F.sql_expr("PARSE_JSON(METADATA_JSON)").alias("C_JSON"),
    )
    stored = session.table(contract["TARGET_DIM"]).select(
        F.col(contract["DIM_PK_COLUMN"]).alias("T_KEY"),
        F.col("METADATA_JSON").alias("T_JSON"),
    )
    pairs = candidate.join(stored, candidate["C_KEY"] == stored["T_KEY"], "left")
    missing_keys = pairs.filter(F.col("T_KEY").is_null()).count()
    change_rows = pairs.filter(F.sql_expr("C_JSON IS DISTINCT FROM T_JSON"))
    changed_paths = {
        row["OSCAL_PATH"]: int(row["N"])
        for row in change_rows.group_by("OSCAL_PATH").agg(
            F.count(F.lit(1)).alias("N")).collect()
    }
    expected_paths = {
        "catalog.groups[].groups[]": 10566,
        "catalog.groups[].groups[].groups[]": 20000,
    }
    all_covered = all(r["records_checked"] ==
                      r["source_populated"] + r["source_empty_target_omitted"]
                      and r["source_populated"] == r["exact_value_matches"]
                      for r in results)
    mismatches = sum(r["mismatches"] for r in results)
    no_source_fields = [r["field"] for r in results if r["source_populated"] == 0]
    passed = (all_covered and mismatches == 0 and
              changed_paths == expected_paths and missing_keys == 0 and
              source_id_differences == 0)
    answer = {
        "status": "SOURCE_TWO_75_ROW_CATALOG_FIVE_NEW_FIELDS_READ_ONLY_QA",
        "writes_executed": False,
        "mapping_fingerprint_matches_preview": True,
        "selected_catalog_mapping_rules": len(rows),
        "field_results": results,
        "field_mismatches_total": mismatches,
        "fields_with_no_populated_source_data": no_source_fields,
        "source_content_id_vs_root_id_differences": source_id_differences,
        "missing_dim_target_keys": missing_keys,
        "updated_path_counts": dict(sorted(changed_paths.items())),
        "changed_path_gate": "PASS" if changed_paths == expected_paths
                            and missing_keys == 0 else "BLOCKED",
        "result": (
            "PASS_VALUES_AND_PATHS_SOURCE_EMPTY_FIELDS_UNTESTED" if no_source_fields
            else "PASS_ALL_FIVE_NEW_FIELDS_VALUES_AND_PATHS"
        ) if passed else "BLOCKED_DO_NOT_COMMIT",
    }
    print(json.dumps(answer, indent=2, sort_keys=True))
    if not passed:
        raise RuntimeError("SOURCE_TWO_NEXT_FIVE_QA_REVIEW_REQUIRED")
    return answer


SOURCE_TWO_NEXT_FIVE_QA = run_catalog_new_five_qa()
