# Paste into a new Python cell after the completed Catalog reference Preview.
# The installed notebook supplies the route, cross-reference, and source tables.
# Run this cell once, then run Cell 7 in PREVIEW. No settings to enter.

from collections import defaultdict
from decimal import Decimal
import hashlib
import json


def _catalog_reference_targets(binding):
    return binding["targets"] if "targets" in binding else [binding]


def _catalog_hierarchy_members(raw, counts):
    identifiers = {}
    if raw is None:
        return identifiers
    for member in raw if isinstance(raw, list) else [raw]:
        fields = {key.lower(): value for key, value in member.items()} if isinstance(member, dict) else {}
        identifier = fields.get("contentid") if isinstance(member, dict) else member
        try:
            content_id = _source_id(str(identifier) if isinstance(identifier, Decimal) else identifier)
            level, module = tuple(_source_id(str(fields[key])) if fields.get(key) is not None else None
                                  for key in ("levelid", "moduleid"))
        except CatalogControlError:
            counts["invalid_members"] += 1
            continue
        identifiers.setdefault(content_id, set()).add((level, module))
    return identifiers


def _apply_native_catalog_control_hierarchy(nodes, edges, target_values, context, spec, snapshots, known_levels):
    hierarchy = spec["control_hierarchy_reference"]
    field = hierarchy["source_field"]
    frame = context["lookups"].get("native_control_guid_metadata", {}).get(spec["lookup"])
    if frame is None:
        raise ValueError("Catalog hierarchy requires the frozen Archer field metadata")
    matching_fields = []
    source_level = spec["guid_props"]["level_id"]
    for raw in frame.to_local_iterator():
        row = raw.as_dict(recursive=True) if hasattr(raw, "as_dict") else dict(raw)
        if row["LEVEL_ID"] == source_level and row["FIELD_ID"] == hierarchy["field_id"]:
            matching_fields.append(row["SQL_FIELD_NAME"])
    if matching_fields != [field]:
        raise ValueError("Catalog hierarchy requires the exact Control Standard cross-reference binding")

    binding = next(prop for prop in spec["extra_props"] if prop["source_field"] == field)
    targets = {str(item["target_level_id"]): item for item in _catalog_reference_targets(binding["reference"])}
    subsection_level = str(hierarchy["target_level_id"])
    section_level = str(hierarchy["target_level_id"] - 1)
    subsection = targets[subsection_level]
    section = targets[section_level]
    joined = context["lookups"]["joined_contract"]
    parent_field = joined[hierarchy["subsection_lookup"]]["join_json_array_field"]
    counts = dict(standard_references=0, subsection_members=0, resolved_subsections=0,
                  missing_subsections=0, missing_subsection_names=0, outside_target_level=0,
                  unknown_level=0, invalid_members=0, ambiguous_targets=0,
                  missing_parent_bindings=0, ambiguous_parent_bindings=0,
                  invalid_parent_members=0, resolved_sections=0, missing_sections=0,
                  missing_section_names=0, property_occurrences=0, unclassified_property_occurrences=0)

    def target_levels(content_id):
        return [level for level, target in targets.items() if content_id in snapshots[target["lookup_key"]]]

    def conflicts(declarations, level, target):
        return any((declared_level is not None and declared_level != level)
                   or (module is not None and module != str(target["target_module_id"]))
                   for declared_level, module in declarations)

    def payload_for(content_id, level, target, document):
        payload = dict(ContentId=int(content_id), LevelId=int(level), ModuleId=target["target_module_id"])
        name = document.get(target["display_name_field"]) if document is not None else None
        if isinstance(name, str) and name.strip():
            payload["Name"] = name
        return payload

    def parent_section(document):
        invalid = {"invalid_members": 0}
        parents = _catalog_hierarchy_members(document.get(parent_field), invalid)
        if invalid["invalid_members"]:
            counts["invalid_parent_members"] += invalid["invalid_members"]
            return None
        if len(parents) != 1:
            key = "ambiguous_parent_bindings" if parents else "missing_parent_bindings"
            counts[key] += 1
            return None
        content_id, declarations = next(iter(parents.items()))
        levels = target_levels(content_id)
        if (levels and levels != [section_level]) or conflicts(declarations, section_level, section):
            counts["invalid_parent_members"] += 1
            return None
        target = snapshots[section["lookup_key"]].get(content_id)
        payload = payload_for(content_id, section_level, section, target)
        counts["missing_sections" if target is None else "resolved_sections"] += 1
        counts["missing_section_names"] += int(target is not None and "Name" not in payload)
        return payload

    def hierarchy_properties(raw):
        identifiers = _catalog_hierarchy_members(raw, counts)
        counts["standard_references"] += len(identifiers)
        members = []
        unclassified = []
        for content_id in sorted(identifiers, key=int):
            declarations = identifiers[content_id]
            levels = target_levels(content_id)
            if len(levels) > 1:
                counts["ambiguous_targets"] += 1
                continue
            declared = {level for level, _ in declarations if level is not None}
            if len(declared) > 1:
                counts["invalid_members"] += 1
                continue
            level = levels[0] if levels else known_levels.get(content_id, next(iter(declared), None))
            if level is None:
                counts["unknown_level"] += 1
                unclassified.append({"ContentId": int(content_id)})
                continue
            if level not in targets or conflicts(declarations, level, targets[level]):
                counts["invalid_members"] += 1
                continue
            if level != subsection_level:
                counts["outside_target_level"] += 1
                continue
            document = snapshots[subsection["lookup_key"]].get(content_id)
            payload = payload_for(content_id, level, subsection, document)
            counts["missing_subsections" if document is None else "resolved_subsections"] += 1
            counts["missing_subsection_names"] += int(document is not None and "Name" not in payload)
            if document is not None and (parent := parent_section(document)) is not None:
                payload["Section"] = parent
            members.append(payload)
        counts["subsection_members"] += len(members)
        values = (("authoritative-subsection-reference", "property_occurrences", members),
                  ("authoritative-source-unclassified-reference", "unclassified_property_occurrences", unclassified))
        return [(name, counter, _metadata_json_text(items)) for name, counter, items in values if items]

    control_paths = set(spec["paths"])
    members_by_standard = {}
    namespace = binding["namespace"]
    for node in nodes:
        if node["ELEMENT_PATH"] not in control_paths:
            continue
        content_id = node["INSTANCE_KEY"]
        if content_id not in members_by_standard:
            members_by_standard[content_id] = hierarchy_properties(target_values[content_id].get(field))
        values = members_by_standard[content_id]
        if not values:
            continue
        payload = json.loads(node["METADATA_JSON"])
        props = payload.setdefault("props", [])
        for name, counter, value in values:
            if any(prop.get("name") == name and prop.get("ns") == namespace for prop in props):
                raise ValueError("Duplicate native Catalog hierarchy reference property")
            props.append(dict(name=name, ns=namespace, value=value))
            counts[counter] += 1
        node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
    context["graph_report"]["NATIVE_CATALOG_CONTROL_HIERARCHY"] = {field: counts}
    return nodes, edges


def install_catalog_hierarchy_preview():
    report = globals().get("PIPELINE_REPORT") or {}
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if (len(contexts) != 1 or report.get("status") != "PREVIEW_COMPLETE"
            or report.get("writes_executed") is not False
            or globals().get("OSCAL_LOAD_MODE") != "PREVIEW"):
        raise ValueError("Use the notebook session with the completed write-disabled Catalog reference Preview.")
    context = contexts[0]
    route, config, plan = context["route"], context["config"], context["compiled_plan"]
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native.get("guid_props") or native.get("control_hierarchy_reference")):
        raise ValueError("Use the existing write-disabled Catalog reference Preview.")
    groups = [group for group in report["groups"]
              if (group["source"], group["model"]) == (context["source_key"], "CATALOG")]
    inventory = globals().get("CATALOG_REFERENCE_INVENTORY") or {}
    group = groups[0] if len(groups) == 1 else {}
    report_stats = group.get("native_catalog", {}).get("NATIVE_CATALOG_RECORD_REFERENCES", {})
    fields = [field for field, stats in report_stats.items() if stats.get("missing_targets")]
    inventory_rows = [row for row in inventory.get("fields", []) if row["source_field"] in fields]
    if len(fields) != 1 or len(inventory_rows) != 1:
        raise ValueError("Use the completed Catalog reference Preview that isolated one missing reference field.")
    field = fields[0]
    domain = {row["level_id"]: row["module_id"] for row in inventory_rows[0]["target_domains"]}
    owners = native.get("owner_bindings", native.get("declared_owner_bindings", {}))
    joined = route.get("joined_lookups", {})
    if not domain or not owners:
        raise ValueError("Catalog reference inventory or group lookups are missing.")
    deepest = max(owners, key=lambda path: path.count("."))
    subsection_binding = owners[deepest]
    section_binding = joined[subsection_binding]["parent_binding"]
    subsection_level = max(domain)
    section_level = subsection_level - 1
    target_configs = _catalog_preview_targets(context, native, set(domain))
    if (not set(domain).issubset(target_configs)
            or target_configs[subsection_level][1:4] != (None, None, subsection_binding)
            or section_level not in domain
            or target_configs[section_level][1:4] != (None, None, section_binding)):
        raise ValueError("The selected cross-reference does not match the configured Section and Subsection chain.")

    lookup = native["lookup"]
    store = SOURCE_INPUTS[context["source_key"]]["lookups_by_model"]["CATALOG"]
    field_metadata = store["native_control_guid_metadata"][lookup]
    field_ids = [int(row["FIELD_ID"]) for row in field_metadata.to_local_iterator()
                 if row["LEVEL_ID"] == native["guid_props"]["level_id"] and row["SQL_FIELD_NAME"] == field]
    if len(field_ids) != 1 or field_ids[0] <= 0:
        raise ValueError("The Catalog cross-reference has no unique Archer field identity.")

    base_apply = _native_catalog_apply
    base_fingerprint = plan["mapping_fingerprint"]
    existing_fingerprint = getattr(base_apply, "catalog_hierarchy_fingerprint", None)
    if existing_fingerprint == base_fingerprint:
        base_fingerprint = base_apply.catalog_hierarchy_base_fingerprint
        base_apply = base_apply.catalog_hierarchy_base_apply
    reference = getattr(base_apply, "catalog_guidance_base_apply", base_apply)
    if not getattr(reference, "catalog_reference_batch_base_apply", None):
        raise ValueError("The Catalog reference Preview helper must be active in this session.")

    snapshots, handles, targets = {}, [], []
    standard = route["native_controls"][lookup]
    for level, module in sorted(domain.items()):
        observed_module, source_key, model, binding, title = target_configs[level]
        if module != observed_module or binding == "native":
            raise ValueError("The selected field does not have the expected external reference domains.")
        source_route = route if source_key is None else ROUTES[(source_key, model)]
        target = source_route["joined_lookups"][binding] if binding else source_route
        frame, _, handle = load_source_input(session, {
            "source_table": target["source_table"],
            "source_id_column": target.get("source_id_column", target.get("content_id_column", "CONTENT_ID")),
            "source_json_column": target.get("source_json_column", target.get("json_column", "CURATED_JSON")),
            "source_order": target.get("source_order", target.get(
                "order_candidates", standard.get("order_candidates", ()) if binding else ())),
        })
        handles.append(handle)
        table_key = str(level)
        snapshots[table_key] = {_source_id(row["SOURCE_RECORD_ID"]): _metadata_parse(row, context)
                                for row in frame.to_local_iterator()}
        targets.append(dict(lookup_key=table_key, target_level_id=level,
                            target_module_id=module, display_name_field=title))

    standard_frame = store["native_control_sources"][lookup]
    standard_values = {
        _source_id(row["SOURCE_RECORD_ID"]): _metadata_parse(row, context)
        for row in standard_frame.to_local_iterator()
    }
    absent_ids = set()
    available = set().union(*(snapshot for snapshot in snapshots.values()))
    for row in standard_values.values():
        references = _catalog_hierarchy_members(row.get(field), {"invalid_members": 0})
        absent_ids.update(references.keys() - available)
    metadata_table = native["guid_props"]["metadata_table"]
    if not metadata_table.upper().endswith("_FIELD"):
        raise ValueError("The notebook does not expose the expected Archer Content metadata.")
    content_metadata = _input_table(session, metadata_table[:-len("_FIELD")] + "_CONTENT")
    cols = _normalized_columns(content_metadata.columns)
    content_id = _input_column(cols, "CONTENT_ID")
    level_id = _input_column(cols, "LEVEL_ID")
    if content_id is None or level_id is None:
        raise ValueError("Archer Content metadata is missing its Content and Level columns.")
    levels = defaultdict(set)
    ordered_ids = sorted(absent_ids, key=int)
    candidates = content_metadata.select(col(content_id).cast("string").alias("CONTENT_ID"),
                                         col(level_id).alias("LEVEL_ID"))
    for start in range(0, len(ordered_ids), 500):
        batch = candidates.filter(col("CONTENT_ID").in_(ordered_ids[start:start + 500])).distinct()
        for row in batch.to_local_iterator():
            if row["LEVEL_ID"] is not None:
                levels[row["CONTENT_ID"]].add(str(row["LEVEL_ID"]))
    known_levels = {key: next(iter(values)) for key, values in levels.items() if len(values) == 1}

    spec = {**native, "control_hierarchy_reference": dict(
        source_field=field, field_id=field_ids[0], target_level_id=subsection_level,
        subsection_lookup=subsection_binding, section_lookup=section_binding)}
    spec["extra_props"] = [{"source_field": field, "namespace": "urn:archer:source:v1",
                            "reference": {"targets": targets}}]
    fingerprint = hashlib.sha256(json.dumps(
        [base_fingerprint, "catalog-hierarchy-preview-v1", spec["control_hierarchy_reference"], domain],
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()

    def apply_hierarchy(nodes, edges, source_df, active):
        active_plan = active["compiled_plan"]
        if (active["config"].get("WRITE_ALLOWED") is not False
                or active["config"].get("EXECUTE_WRITES") is not False
                or active_plan.get("mapping_fingerprint") != fingerprint):
            raise ValueError("The Catalog hierarchy helper requires the selected write-disabled Preview.")
        active_plan["mapping_fingerprint"] = base_fingerprint
        try:
            new_nodes, new_edges = base_apply(nodes, edges, source_df, active)
            base_result_fingerprint = active_plan["mapping_fingerprint"]
        finally:
            active_plan["mapping_fingerprint"] = fingerprint
        if base_result_fingerprint != base_fingerprint:
            active_plan["mapping_fingerprint"] = hashlib.sha256(json.dumps(
                [base_result_fingerprint, fingerprint], separators=(",", ":")
            ).encode("utf-8")).hexdigest()
        return _apply_native_catalog_control_hierarchy(
            new_nodes, new_edges, standard_values, active, spec, snapshots, known_levels)

    apply_hierarchy.catalog_hierarchy_base_apply = base_apply
    apply_hierarchy.catalog_hierarchy_base_fingerprint = base_fingerprint
    apply_hierarchy.catalog_hierarchy_fingerprint = fingerprint
    apply_hierarchy.catalog_hierarchy_snapshots = handles
    plan["mapping_fingerprint"] = fingerprint
    return apply_hierarchy


_native_catalog_apply = install_catalog_hierarchy_preview()
print("Catalog hierarchy ready. Run Cell 7 in PREVIEW. Review NATIVE_CATALOG_CONTROL_HIERARCHY.")
