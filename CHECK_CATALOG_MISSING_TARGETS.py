# Run in a new Python cell after the completed Catalog reference Preview.
# This reports counts only. It reads the existing Preview and Archer metadata.

from collections import Counter, defaultdict
import json


def check_catalog_missing_targets():
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

    fields = {}
    for field, counts in missing_by_field.items():
        by_level = defaultdict(lambda: {"missing_pairs": 0, "distinct_target_ids": 0})
        for target, quantity in counts.items():
            target_levels = levels[target]
            label = (next(iter(target_levels)) if len(target_levels) == 1
                     else "ambiguous_level" if target_levels else "unknown_level")
            by_level[label]["missing_pairs"] += quantity
            by_level[label]["distinct_target_ids"] += 1
        fields[field] = {
            "missing_pairs": sum(counts.values()),
            "distinct_target_ids": len(counts),
            "by_archer_level": dict(by_level),
        }
    return {"status": "CATALOG_MISSING_TARGET_CHECK_COMPLETE", "fields": fields}


print(json.dumps(check_catalog_missing_targets(), indent=2, sort_keys=True))
