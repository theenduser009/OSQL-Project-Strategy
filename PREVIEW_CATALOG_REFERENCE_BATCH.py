# Snowflake notebook. Keep the accepted Catalog property mapping and Preview mode.
# Paste the private CATALOG_REFERENCE_BATCH assignment above this code in a
# new Python cell after Cell 4. Run this cell, then run Cells 5–7.

from collections import defaultdict
import hashlib
import json
import re


def install_catalog_reference_batch_preview():
    contexts = globals().get("MAPPING_CONTEXTS") or []
    manifest = globals().get("CATALOG_REFERENCE_BATCH")
    if not isinstance(manifest, dict) or set(manifest) != {"fields", "raw", "targets"}:
        raise ValueError("Paste the CATALOG_REFERENCE_BATCH assignment above this cell first.")
    if len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW":
        raise ValueError("Run Cells 1–4 with only the Authoritative Sources Catalog Preview selected.")
    current = contexts[0]
    route, config, plan = current["route"], current["config"], current["compiled_plan"] or {}
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native.get("guid_props")):
        raise ValueError("Use the write-disabled Catalog property baseline and rerun Cells 1–4.")

    fields, raw_fields, targets = manifest["fields"], manifest["raw"], manifest["targets"]
    prior_field = native["guid_props"]["source_field"]
    if not isinstance(fields, dict) or prior_field not in fields or not isinstance(targets, dict):
        raise ValueError("The batch must include the existing Procedure field and target routes.")
    if (not isinstance(raw_fields, (list, tuple)) or len(set(raw_fields)) != len(raw_fields)
            or set(raw_fields).intersection(fields)
            or any(not isinstance(field, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", field)
                   for field in [*fields, *raw_fields])
            or any(not isinstance(levels, (list, tuple)) or not levels or len(set(levels)) != len(levels)
                   or any(type(level) is not int or level <= 0 or level not in targets for level in levels)
                   for levels in fields.values())):
        raise ValueError("The Catalog reference batch has invalid field declarations.")
    used_levels = sorted({level for levels in fields.values() for level in levels})
    namespace = "urn:archer:source:v1"
    new_names = {field: field.lower().replace("_", "-") for field in [*fields, *raw_fields]}
    if len(set(new_names.values())) != len(new_names):
        raise ValueError("The batch has duplicate Catalog property names.")
    existing = {(prop["property_name"], prop["namespace"], prop.get("class")): prop["source_field"]
                for prop in native.get("extra_props", ())}
    if any((name, namespace, None) in existing for name in new_names.values()):
        raise ValueError("The installed mapping already contains one or more of these Catalog properties.")

    standard_lookup = native["lookup"]
    standard_input = route["native_controls"][standard_lookup]
    field_binding = route["native_control_guid_properties"][standard_lookup]
    metadata = _input_table(session, field_binding["metadata_table"])
    columns = _normalized_columns(metadata.columns)
    level_col = _input_column(columns, field_binding["level_id_column"])
    module_col = _input_column(columns, "MODULE_ID")
    if level_col is None or module_col is None:
        raise ValueError("Archer field metadata needs level and module columns.")
    domains = defaultdict(set)
    for row in (metadata.filter(col(level_col).in_(used_levels) & col(module_col).is_not_null())
                .select(col(level_col).alias("LEVEL_ID"), col(module_col).alias("MODULE_ID"))
                .distinct().to_local_iterator()):
        domains[int(row["LEVEL_ID"])].add(int(row["MODULE_ID"]))

    transport = SOURCE_INPUTS[current["source_key"]]["lookups_by_model"]["CATALOG"]
    standard_frame = transport["native_control_sources"][standard_lookup]
    tables, target_names, modules, snapshots = {}, {}, {}, []
    for level in used_levels:
        module, source_key, model, binding, name_field = targets[level]
        if type(module) is not int or domains[level] != {module}:
            raise ValueError(f"Archer metadata did not confirm the configured module for Level {level}.")
        modules[level] = module
        target_route = route if source_key is None else ROUTES[(source_key, model)]
        if binding == "native":
            target_config = standard_input
            frame = standard_frame
        else:
            target_config = target_route["joined_lookups"][binding] if binding else target_route
            frame, _, snapshot = load_source_input(session, {
                "source_table": target_config["source_table"],
                "source_id_column": target_config.get("source_id_column", target_config.get("content_id_column", "CONTENT_ID")),
                "source_json_column": target_config.get("source_json_column", target_config.get("json_column", "CURATED_JSON")),
                "source_order": target_config.get("source_order", target_config.get(
                    "order_candidates", standard_input.get("order_candidates", ()) if binding else ())),
            })
            snapshots.append(snapshot)
        tables[level] = target_config["source_table"]
        names = {}
        for record in frame.to_local_iterator():
            record_id = _source_id(record["SOURCE_RECORD_ID"])
            if record_id in names:
                raise ValueError(f"Archer Level {level} has duplicate target Content IDs.")
            name = _metadata_parse(record, current).get(name_field)
            names[record_id] = name if isinstance(name, str) and name.strip() else None
        target_names[level] = names

    baseline = plan.get("catalog_reference_batch_base", plan.get("procedure_reference_preview_base", plan["mapping_fingerprint"]))
    fingerprint = hashlib.sha256(json.dumps(
        [baseline, "catalog-reference-batch-preview-v1", fields, raw_fields, targets, tables],
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    base_apply = getattr(_native_catalog_apply, "catalog_reference_batch_base_apply",
                         getattr(_native_catalog_apply, "procedure_reference_preview_base", _native_catalog_apply))

    def resolve(raw, allowed, counts):
        identifiers = defaultdict(set)
        members = raw if isinstance(raw, list) else [] if raw is None else [raw]
        for member in members:
            keys = {key.lower(): value for key, value in member.items()} if isinstance(member, dict) else {}
            try:
                record_id = _source_id(keys.get("contentid") if isinstance(member, dict) else member)
            except CatalogControlError:
                counts["invalid_members"] += 1
                continue
            level, module = keys.get("levelid"), keys.get("moduleid")
            if level is not None and str(level) not in {str(target) for target in allowed}:
                counts["invalid_members"] += 1
                continue
            identifiers[record_id].add((None if level is None else str(level),
                                        None if module is None else str(module)))
        counts["references"] += len(identifiers)
        values = []
        for record_id in sorted(identifiers, key=int):
            matches = [level for level in allowed if record_id in target_names[level]]
            if not matches:
                counts["missing_targets"] += 1
                continue
            if len(matches) != 1:
                counts["ambiguous_targets"] += 1
                continue
            level = matches[0]
            module = modules[level]
            if any((declared_level is not None and declared_level != str(level))
                   or (declared_module is not None and declared_module != str(module))
                   for declared_level, declared_module in identifiers[record_id]):
                counts["invalid_members"] += 1
                continue
            name = target_names[level][record_id]
            if name is None:
                counts["missing_names"] += 1
                continue
            values.append({"ContentId": int(record_id), "ModuleId": module, "Name": name})
        counts["resolved"] += len(values)
        return values

    def apply_catalog_reference_batch(nodes, edges, source_df, context):
        current_config = context["config"]
        if (current_config.get("WRITE_ALLOWED") is not False or current_config.get("EXECUTE_WRITES") is not False
                or context["compiled_plan"].get("mapping_fingerprint") != fingerprint):
            raise ValueError("Rerun this batch cell for the selected write-disabled Preview.")
        result_nodes, result_edges = base_apply(nodes, edges, source_df, context)
        controls = [node for node in result_nodes if node["ELEMENT_PATH"] in native["paths"]]
        owners = {node["INSTANCE_KEY"] for node in controls}
        counts = {field: dict(references=0, resolved=0, invalid_members=0, missing_targets=0,
                              missing_names=0, ambiguous_targets=0) for field in fields}
        property_values = {}
        frame = context["lookups"]["native_control_sources"][standard_lookup]
        for record in frame.to_local_iterator():
            owner = _source_id(record["SOURCE_RECORD_ID"])
            if owner not in owners:
                continue
            doc = _metadata_parse(record, context)
            values = {field: _metadata_json_text(doc[field]) for field in raw_fields if doc.get(field) is not None}
            for field, allowed in fields.items():
                resolved = resolve(doc.get(field), allowed, counts[field])
                if resolved:
                    values[field] = _metadata_json_text(resolved)
            property_values[owner] = values
        if set(property_values) != owners:
            raise ValueError("A Catalog control is missing from the frozen Control Standards input.")

        occurrences = 0
        for node in controls:
            values = property_values[node["INSTANCE_KEY"]]
            if not values:
                continue
            payload = json.loads(node["METADATA_JSON"])
            props = payload["props"]
            for field, value in sorted(values.items()):
                name = new_names[field]
                if any(prop["name"] == name and prop.get("ns") == namespace and prop.get("class") is None for prop in props):
                    raise ValueError("Duplicate Catalog property in Preview.")
                index = next((i for i, prop in enumerate(props)
                              if existing.get((prop["name"], prop.get("ns"), prop.get("class")), "") > field), len(props))
                props.insert(index, {"name": name, "ns": namespace, "value": value})
                occurrences += 1
            node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
        report = context["graph_report"]
        report["NATIVE_CATALOG_EXTRA_PROP_OCCURRENCES"] = report.get("NATIVE_CATALOG_EXTRA_PROP_OCCURRENCES", 0) + occurrences
        report["NATIVE_CATALOG_RECORD_REFERENCES"] = counts
        return result_nodes, result_edges

    apply_catalog_reference_batch.catalog_reference_batch_base_apply = base_apply
    apply_catalog_reference_batch.catalog_reference_batch_snapshots = snapshots
    plan["catalog_reference_batch_base"] = baseline
    plan["mapping_fingerprint"] = fingerprint
    return apply_catalog_reference_batch


_native_catalog_apply = install_catalog_reference_batch_preview()
print("Catalog reference batch ready. Run Cells 5–7 in PREVIEW.")
