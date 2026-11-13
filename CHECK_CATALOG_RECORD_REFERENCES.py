# Paste into a new Python cell in your existing Catalog DEV notebook.
# Run only this cell after the Catalog Preview. It reads the current input snapshot
# and Archer metadata and prints counts. It does not modify the mapper or its targets.

from collections import Counter, defaultdict
from urllib.parse import urlsplit
import json


def check_catalog_record_references():
    active = [c for c in (globals().get("MAPPING_CONTEXTS") or [])
              if c["config"].get("OSCAL_MODEL") == "CATALOG"
              and (c["compiled_plan"] or {}).get("native_catalog", {}).get("guid_props")]
    if len(active) != 1:
        raise ValueError("Run this in the notebook that just completed the Control Standards Catalog Preview.")
    context = active[0]
    native = context["compiled_plan"]["native_catalog"]
    lookup = native["lookup"]
    source_input = (globals().get("SOURCE_INPUTS") or {}).get(context["source_key"], {})
    frame = source_input.get("lookups_by_model", {}).get("CATALOG", {}).get("native_control_sources", {}).get(lookup)
    if frame is None:
        raise ValueError("The Catalog input snapshot is missing. Use the same session as the completed Preview.")
    graph = (globals().get("MODEL_GRAPHS") or {}).get((context["source_key"], "CATALOG"))
    if not graph:
        raise ValueError("The Catalog Preview graph is missing. Use the same session as the completed Preview.")

    binding = context["route"]["native_control_guid_properties"][lookup]
    field_metadata = _input_table(session, binding["metadata_table"])
    metadata_name = binding["metadata_table"]
    if not metadata_name.upper().endswith("_FIELD"):
        raise ValueError("The configured field metadata does not use the Archer metadata naming convention.")
    content_metadata_name = metadata_name[:-len("_FIELD")] + "_CONTENT"
    content_metadata = _input_table(session, content_metadata_name)

    def columns(table, *required):
        names = _normalized_columns(table.columns)
        result = [_input_column(names, name) for name in required]
        if any(name is None for name in result):
            raise ValueError("The notebook's Archer metadata is missing required columns.")
        return result

    def identifier(value):
        if value is None:
            return None
        try:
            return _source_id(str(value))
        except CatalogControlError:
            return None

    def http_url(member):
        candidates = [member] if isinstance(member, str) else (
            [value for key, value in member.items() if key.lower() in {"url", "href"}]
            if isinstance(member, dict) else [])
        for value in candidates:
            if not isinstance(value, str) or any(char.isspace() for char in value.strip()):
                continue
            try:
                url = urlsplit(value.strip())
                if url.scheme in {"http", "https"} and url.hostname:
                    return True
            except ValueError:
                continue
        return False

    level, field, field_type, module = columns(
        field_metadata, binding["level_id_column"], binding["source_field_column"],
        "FIELD_TYPE_ID", "MODULE_ID")
    metadata = field_metadata.select(
        col(level).alias("LEVEL_ID"), col(field).alias("FIELD_KEY"),
        col(field_type).alias("FIELD_TYPE"), col(module).alias("MODULE_ID")).distinct()
    reference_fields = set()
    modules_by_level = defaultdict(set)
    source_level = str(binding["level_id"])
    for row in metadata.to_local_iterator():
        level_id = identifier(row["LEVEL_ID"])
        module_id = identifier(row["MODULE_ID"])
        if level_id is not None and module_id is not None:
            modules_by_level[level_id].add(module_id)
        if level_id == source_level and str(row["FIELD_TYPE"]) in {"9", "23"} and row["FIELD_KEY"]:
            reference_fields.add(row["FIELD_KEY"])

    nodes = graph["nodes"]
    path_column, instance_column = columns(nodes, "ELEMENT_PATH", "INSTANCE_KEY")
    control_ids = {
        str(row["INSTANCE_KEY"]) for row in nodes.filter(col(path_column).in_(native["paths"]))
        .select(col(instance_column).alias("INSTANCE_KEY")).distinct().to_local_iterator()
    }
    if not control_ids:
        raise ValueError("No Control Standards were found in this Catalog Preview graph.")
    graph_report = graph["context"]["graph_report"]
    completed_fields = {
        key for key, stats in graph_report.get("NATIVE_CATALOG_RECORD_REFERENCES", {}).items()
        if stats.get("resolved", 0) > 0
        and stats.get("resolved") == stats.get("references")
        and not any(stats.get(k, 0) for k in ("invalid_members", "missing_targets", "missing_names"))
    }
    reference_fields.difference_update(completed_fields)
    references = defaultdict(Counter)
    counts = defaultdict(Counter)
    all_ids = set()
    scanned_ids = set()
    for row in frame.to_local_iterator():
        owner_id = str(row["SOURCE_RECORD_ID"])
        if owner_id not in control_ids:
            continue
        scanned_ids.add(owner_id)
        doc = _metadata_parse(row, context)
        for field_key, value in doc.items():
            if field_key in completed_fields or value is None or value == [] or value == {} or value == "":
                continue
            members = value if isinstance(value, list) else [value]
            populated = False
            for member in members:
                if member is None or member == "" or member == {} or member == []:
                    continue
                if http_url(member):
                    counts[field_key]["http_url_members"] += 1
                    populated = True
                if isinstance(member, dict):
                    keys = {key.lower(): value for key, value in member.items()}
                    if "contentid" not in keys:
                        continue
                    raw_id, raw_level, raw_module = keys["contentid"], keys.get("levelid"), keys.get("moduleid")
                elif field_key in reference_fields:
                    raw_id, raw_level, raw_module = member, None, None
                else:
                    continue
                content_id, level_id = identifier(raw_id), identifier(raw_level)
                module_id = identifier(raw_module)
                populated = True
                if (content_id is None or (raw_level is not None and level_id is None)
                        or (raw_module is not None and module_id is None)):
                    counts[field_key]["invalid_reference_members"] += 1
                    continue
                all_ids.add(content_id)
                references[field_key][content_id, level_id, module_id] += 1
            if populated:
                counts[field_key]["populated_controls"] += 1
    if scanned_ids != control_ids:
        raise ValueError("The Preview graph and Control Standards input snapshot do not match.")

    content_id_column, level_column = columns(content_metadata, "CONTENT_ID", "LEVEL_ID")
    levels_by_content = defaultdict(set)
    target_ids = sorted(all_ids, key=int)
    metadata_pairs = content_metadata.select(
        col(content_id_column).cast("string").alias("CONTENT_ID"), col(level_column).alias("LEVEL_ID"))
    for start in range(0, len(target_ids), 500):
        for row in metadata_pairs.filter(col("CONTENT_ID").in_(target_ids[start:start + 500])).distinct().to_local_iterator():
            target_level = identifier(row["LEVEL_ID"])
            if target_level is not None:
                levels_by_content[row["CONTENT_ID"]].add(target_level)

    rows = []
    for field_key in sorted(counts):
        stats = counts[field_key]
        target_domains = Counter()
        for (content_id, declared_level, declared_module), quantity in references[field_key].items():
            stats["record_reference_members"] += quantity
            levels = levels_by_content[content_id]
            if len(levels) != 1:
                stats["unresolved_level_members"] += quantity
                continue
            target_level = next(iter(levels))
            if declared_level is not None and declared_level != target_level:
                stats["level_mismatch_members"] += quantity
                continue
            modules = modules_by_level[target_level]
            module_id = next(iter(modules)) if len(modules) == 1 else None
            if module_id is None:
                stats["unresolved_module_members"] += quantity
            elif declared_module is not None and declared_module != module_id:
                stats["module_mismatch_members"] += quantity
                continue
            else:
                stats["level_and_module_resolved_members"] += quantity
            target_domains[(target_level, module_id)] += quantity
        rows.append({"source_field": field_key, **{
            key: stats[key] for key in ("populated_controls", "http_url_members",
                "record_reference_members", "invalid_reference_members", "unresolved_level_members",
                "level_mismatch_members", "module_mismatch_members", "unresolved_module_members",
                "level_and_module_resolved_members")},
            "target_domains": [{"level_id": int(level_id), "module_id": int(module_id) if module_id else None,
                                "members": qty} for (level_id, module_id), qty in
                               sorted(target_domains.items(), key=lambda item: int(item[0][0]))]})
    rows.sort(key=lambda row: (-row["populated_controls"], row["source_field"]))
    return {"status": "REFERENCE_INVENTORY_COMPLETE", "completed_fields_excluded": sorted(completed_fields),
            "catalog_controls_checked": len(scanned_ids),
            "other_reference_fields_without_detected_values": sorted(reference_fields - counts.keys()),
            "display_name_check": "Pending target field binding", "fields": rows}


CATALOG_REFERENCE_INVENTORY = check_catalog_record_references()
print(json.dumps(CATALOG_REFERENCE_INVENTORY, indent=2))
