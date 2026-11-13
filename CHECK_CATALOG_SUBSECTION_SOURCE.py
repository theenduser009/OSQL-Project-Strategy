# Run in a new Python cell after the completed Catalog reference Preview.
# This reports counts only. It compares the completed Preview with the currently configured Subsection source.

from collections import Counter, defaultdict
import json


def check_catalog_subsection_source():
    report = globals().get("PIPELINE_REPORT") or {}
    graphs = globals().get("MODEL_GRAPHS") or {}
    groups = [group for group in report.get("groups", [])
              if group.get("model") == "CATALOG"
              and group.get("native_catalog", {}).get("NATIVE_CATALOG_RECORD_REFERENCES")]
    if (report.get("status") != "PREVIEW_COMPLETE" or report.get("writes_executed") is not False
            or len(groups) != 1):
        raise ValueError("Use the same session as the completed Catalog reference Preview.")

    group = groups[0]
    stats = group["native_catalog"]["NATIVE_CATALOG_RECORD_REFERENCES"]
    missing_fields = {field: counts for field, counts in stats.items() if counts["missing_targets"]}
    if not missing_fields:
        return {"status": "NO_MISSING_CATALOG_TARGETS"}
    if any(counts.get(key, 0) for counts in missing_fields.values()
           for key in ("invalid_members", "missing_names", "ambiguous_targets")):
        raise ValueError("Other resolution errors are present. The counts cannot isolate missing targets.")

    graph = graphs.get((group["source"], group["model"]))
    if not graph:
        raise ValueError("The completed Catalog Preview graph is missing.")
    context = graph["context"]
    plan = context["compiled_plan"]
    if plan["mapping_fingerprint"] != group["mapping_fingerprint"]:
        raise ValueError("The Catalog graph and Preview report do not match.")
    native = plan["native_catalog"]
    lookup = native["lookup"]
    source = context["lookups"]["native_control_sources"][lookup]

    namespace = "urn:archer:source:v1"
    property_fields = {field.lower().replace("_", "-"): field for field in missing_fields}
    resolved = {}
    nodes = graph["nodes"].filter(col("ELEMENT_PATH").in_(native["paths"]))
    for row in nodes.select("INSTANCE_KEY", "METADATA_JSON").distinct().to_local_iterator():
        owner = _source_id(row["INSTANCE_KEY"])
        payload = row["METADATA_JSON"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        current = {property_fields[prop["name"]]: {
            _source_id(ref["ContentId"]) for ref in json.loads(prop["value"])
        } for prop in payload["props"] if prop.get("ns") == namespace
            and prop.get("name") in property_fields}
        if resolved.setdefault(owner, current) != current:
            raise ValueError("Catalog placements disagree on the references for a Control Standard.")
    if not resolved:
        raise ValueError("The Preview graph contains no Catalog control placements.")

    missing_by_field = {field: Counter() for field in missing_fields}
    references, matched = Counter(), Counter()
    scanned = set()
    for row in source.to_local_iterator():
        owner = _source_id(row["SOURCE_RECORD_ID"])
        if owner not in resolved:
            continue
        if owner in scanned:
            raise ValueError("The frozen input has duplicate Control Standards.")
        scanned.add(owner)
        doc = _metadata_parse(row, context)
        for field in missing_fields:
            raw = doc.get(field)
            members = raw if isinstance(raw, list) else [] if raw is None else [raw]
            ids = set()
            for member in members:
                if isinstance(member, dict):
                    member = {key.lower(): value for key, value in member.items()}["contentid"]
                ids.add(_source_id(member))
            present = resolved[owner].get(field, set())
            if not present <= ids:
                raise ValueError("The Catalog property contains a reference outside the frozen input.")
            references[field] += len(ids)
            matched[field] += len(present)
            missing_by_field[field].update(ids - present)

    if scanned != resolved.keys() or any(
        (references[field], matched[field], sum(missing_by_field[field].values())) !=
        (counts["references"], counts["resolved"], counts["missing_targets"])
        for field, counts in missing_fields.items()
    ):
        raise ValueError("Source and payload counts did not reconcile to the completed Preview report.")

    field_table = context["route"]["native_control_guid_properties"][lookup]["metadata_table"]
    if not field_table.upper().endswith("_FIELD"):
        raise ValueError("The installed route has an unrecognized Archer metadata table name.")
    content_table = _input_table(session, field_table[:-len("_FIELD")] + "_CONTENT")
    columns = _normalized_columns(content_table.columns)
    id_col = _input_column(columns, "CONTENT_ID")
    level_col = _input_column(columns, "LEVEL_ID")
    if id_col is None or level_col is None:
        raise ValueError("Archer content metadata needs Content ID and Level ID columns.")
    metadata = content_table.select(
        col(id_col).cast("string").alias("CONTENT_ID"), col(level_col).alias("LEVEL_ID"))
    target_ids = sorted({target for counts in missing_by_field.values() for target in counts}, key=int)
    levels = defaultdict(set)
    for start in range(0, len(target_ids), 500):
        query = metadata.filter(col("CONTENT_ID").in_(target_ids[start:start + 500])).distinct()
        for row in query.to_local_iterator():
            if row["LEVEL_ID"] is not None:
                levels[row["CONTENT_ID"]].add(str(row["LEVEL_ID"]))


    # The last owner in this native Catalog's route is the Subsection.
    # Compare its physical RAW IDs with the exact missing IDs from the graph.
    owner_bindings = native.get("owner_bindings", native.get("declared_owner_bindings", {}))
    deepest = max(owner_bindings, key=lambda path: path.count("."), default="")
    joined = context["route"].get("joined_lookups", {})
    subsection_binding = owner_bindings.get(deepest)
    subsection = joined.get(subsection_binding, {})
    section_binding = subsection.get("parent_binding")
    section = joined.get(section_binding, {})
    if not subsection.get("source_table") or not section.get("source_table"):
        raise ValueError("The Catalog route does not declare a Subsection and Section source.")
    inventory = globals().get("CATALOG_REFERENCE_INVENTORY") or {}
    catalog_sections = [
        (max(item["target_domains"], key=lambda domain: domain["level_id"])["level_id"], item)
        for item in inventory.get("fields", [])
        if item["source_field"] in missing_by_field and item.get("target_domains")
    ]
    if len(catalog_sections) != 1 or len(missing_by_field) != 1:
        raise ValueError("The Preview inventory does not isolate a single missing reference field.")
    subsection_level, field_info = catalog_sections[0]
    field = field_info["source_field"]
    missing = missing_by_field[field]
    if any(levels[target] != {str(subsection_level)} for target in missing):
        raise ValueError("The missing targets do not all belong to the expected hierarchy level.")

    raw = _input_table(session, subsection["source_table"])
    raw_columns = _normalized_columns(raw.columns)
    raw_id = _input_column(raw_columns, subsection.get("content_id_column", "CONTENT_ID"))
    raw_doc = _input_column(raw_columns, subsection.get("json_column", "CURATED_JSON"))
    if raw_id is None or raw_doc is None:
        raise ValueError("The Subsection source is missing its configured columns.")
    raw_rows = defaultdict(list)
    raw_candidates = raw.select(col(raw_id).cast("string").alias("SOURCE_RECORD_ID"),
                                col(raw_doc).alias("CURATED_JSON"))
    for start in range(0, len(target_ids), 500):
        for row in raw_candidates.filter(col("SOURCE_RECORD_ID").in_(target_ids[start:start + 500])).to_local_iterator():
            raw_rows[row["SOURCE_RECORD_ID"]].append(row)

    joined_sources = context["lookups"].get("joined_sources", {})
    frozen_subsections = joined_sources.get(subsection_binding)
    frozen_sections = joined_sources.get(section_binding)
    if frozen_subsections is None or frozen_sections is None:
        raise ValueError("The completed Preview is missing its frozen Section or Subsection inputs.")
    frozen_ids = set()
    for start in range(0, len(target_ids), 500):
        candidates = frozen_subsections.filter(col("_SOURCE_RECORD_ID").in_(target_ids[start:start + 500]))
        frozen_ids.update(_source_id(row["_SOURCE_RECORD_ID"])
                          for row in candidates.select("_SOURCE_RECORD_ID").distinct().to_local_iterator())
    section_ids = {_source_id(row["_SOURCE_RECORD_ID"])
                   for row in frozen_sections.select("_SOURCE_RECORD_ID").distinct().to_local_iterator()}

    outcomes = defaultdict(lambda: {"distinct_subsections": 0, "affected_pairs": 0})
    parent_field = subsection["join_json_array_field"]
    for target in target_ids:
        records = raw_rows[target]
        if not records:
            reason = "absent_from_current_raw"
        elif len(records) > 1:
            reason = "multiple_raw_rows_review_snapshot_selection"
        elif target in frozen_ids:
            reason = "exists_in_raw_and_joined_preview_input"
        else:
            try:
                raw_parent = _metadata_parse(records[0], context).get(parent_field)
                parent_ids = {_source_id(
                    {key.lower(): value for key, value in item.items()}.get("contentid")
                    if isinstance(item, dict) else item)
                    for item in raw_parent} if isinstance(raw_parent, list) else set()
            except (ValueError, TypeError, CatalogControlError):
                parent_ids = set()
            if len(parent_ids) != 1:
                reason = "exists_in_raw_parent_missing_or_ambiguous"
            elif not parent_ids.intersection(section_ids):
                reason = "exists_in_raw_parent_not_in_preview_input"
            else:
                reason = "exists_in_raw_with_preview_parent_refresh_required"
        outcomes[reason]["distinct_subsections"] += 1
        outcomes[reason]["affected_pairs"] += missing[target]

    return {
        "status": "CATALOG_SUBSECTION_SOURCE_CHECK_COMPLETE",
        "field": field,
        "subsection_level": subsection_level,
        "by_source_status": dict(outcomes),
    }


print(json.dumps(check_catalog_subsection_source(), indent=2, sort_keys=True))
