# Paste this whole file into the extra Python cell after Cell 4 in DEV.
# Run it to see numbered choices. Type the choices below, rerun this cell,
# and run Cells 5–7 in PREVIEW. The installed notebook supplies the configuration.

REFERENCE_ROWS = ()
RAW_PROPERTY_ROWS = ()

from collections import Counter, defaultdict
from urllib.parse import urlsplit
import hashlib
import json
import re


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



def _catalog_preview_targets(current, native, required_levels):
    """Derive target names and locations from the installed mapper and Archer metadata."""
    route = current["route"]
    source_key = current["source_key"]
    guid = route["native_control_guid_properties"][native["lookup"]]
    metadata = _input_table(session, guid["metadata_table"])
    columns = _normalized_columns(metadata.columns)
    level_col = _input_column(columns, guid["level_id_column"])
    module_col = _input_column(columns, "MODULE_ID")
    field_col = _input_column(columns, guid["source_field_column"])
    key_col = _input_column(columns, "KEY_FIELD")
    if any(name is None for name in (level_col, module_col, field_col)):
        raise ValueError("The configured Archer field metadata needs level, module, and source-field columns.")

    row_cache = {}

    def approved_title(key, path, lookup):
        if key not in row_cache:
            configured = ROUTES[(key, "CATALOG")]
            row_cache[key] = load_mapping_rows(MAPPING_FILE, key, configured.get("csv_encoding", "utf-8-sig"))
        names = {row.get("SOURCE_FIELD_NAME") for row in row_cache[key]
                 if row.get("EXECUTION_STATUS") == "APPROVED" and row.get("OSCAL_ELEMENT_PATH") == path
                 and row.get("LOOKUP_KEY") == lookup and row.get("SOURCE_FIELD_NAME")}
        return next(iter(names)) if len(names) == 1 else None

    declarations = {}
    for owner in route.get("owner_procedure_properties", {}).values():
        for binding in owner if isinstance(owner, list) else [owner]:
            if not binding.get("enabled") or binding.get("source_field") != guid["source_field"]:
                continue
            path = binding["owner_path"].removesuffix(".props[]") + ".title"
            lookup = binding.get("joined_lookup")
            title = approved_title(source_key, path, lookup)
            if title:
                declarations[binding["level_id"]] = (None, None, lookup, title)
    declarations[guid["level_id"]] = (None, None, "native", native["fields"]["title"])

    procedures = {}
    for (key, model), candidate in ROUTES.items():
        binding = candidate.get("joined_lookups", {}).get("policy-procedures")
        if binding:
            procedures.setdefault((binding["source_table"], binding["target_level_id"]), (key, model))
    if len(procedures) != 1:
        raise ValueError("The installed routes must declare one Procedure target domain.")
    (_, procedure_level), procedure_route = next(iter(procedures.items()))
    declarations[procedure_level] = (*procedure_route, "policy-procedures", "CONTROL_PROCEDURE_NAME")

    title_routes = {}
    for (key, model), candidate in ROUTES.items():
        if model == "CATALOG" and key != source_key:
            title = approved_title(key, candidate["root"] + ".groups[].title", None)
            if title:
                title_routes.setdefault(title, set()).add((key, model))

    module_levels = {}
    for row in (metadata.filter(col(module_col).is_not_null())
                .select(col(level_col).alias("LEVEL_ID"), col(module_col).alias("MODULE_ID"))
                .distinct().to_local_iterator()):
        if row["LEVEL_ID"] is not None:
            level_id = int(_source_id(str(row["LEVEL_ID"])))
            module_id = int(_source_id(str(row["MODULE_ID"])))
            module_levels.setdefault(level_id, set()).add(module_id)

    title_levels, keyed_levels = {}, {}
    if title_routes:
        projected = [col(level_col).alias("LEVEL_ID"), col(field_col).alias("FIELD_NAME")]
        if key_col is not None:
            projected.append(col(key_col).alias("KEY_FIELD"))
        for row in (metadata.filter(col(field_col).in_(sorted(title_routes)))
                    .select(*projected).distinct().to_local_iterator()):
            if row["LEVEL_ID"] is None:
                continue
            level, title = int(row["LEVEL_ID"]), row["FIELD_NAME"]
            if level in declarations:
                continue
            title_levels.setdefault(title, set()).add(level)
            if key_col is not None and str(row["KEY_FIELD"]).strip().upper() in {"Y", "YES", "TRUE", "KEY", "1"}:
                keyed_levels.setdefault(title, set()).add(level)
    pending = {}
    for title, candidates in title_routes.items():
        levels = keyed_levels.get(title) or title_levels.get(title, set())
        if len(levels) == 1 and len(candidates) == 1:
            level = next(iter(levels))
            pending.setdefault(level, set()).add((*next(iter(candidates)), None, title))
    for level, choices in pending.items():
        if len(choices) == 1:
            declarations[level] = next(iter(choices))

    targets = {}
    for level, binding in declarations.items():
        modules = module_levels.get(level, set())
        if len(modules) == 1:
            targets[level] = (next(iter(modules)), *binding)
    missing = required_levels - targets.keys()
    if missing:
        levels = ", ".join(map(str, sorted(missing)))
        raise ValueError(f"No unique installed target and display-name rule for level(s) {levels}. Check your selected rows.")
    return targets


def _catalog_preview_selection(current, native):
    inventory = globals().get("CATALOG_REFERENCE_INVENTORY")
    if not isinstance(inventory, dict) or not isinstance(inventory.get("fields"), list):
        if not globals().get("MODEL_GRAPHS"):
            raise ValueError("Run the original Catalog Cells 5–7 in PREVIEW once, then rerun this cell.")
        inventory = check_catalog_record_references()
        globals()["CATALOG_REFERENCE_INVENTORY"] = inventory
    existing = {prop["source_field"] for prop in native.get("extra_props", ())}
    prior_field = native["guid_props"]["source_field"]
    candidates = sorted(
        (row for row in inventory["fields"] if row.get("source_field") not in existing | {prior_field}
         and row.get("record_reference_members", 0) > 0
         and row.get("record_reference_members") == row.get("level_and_module_resolved_members")
         and not row.get("invalid_reference_members")),
        key=lambda row: row["source_field"])
    if not REFERENCE_ROWS and not RAW_PROPERTY_ROWS:
        for index, row in enumerate(candidates, 1):
            levels = ", ".join(str(d["level_id"]) for d in row["target_domains"])
            print(f"{index:>3}  {row['source_field']}  |  levels {levels}")
        print("Type the chosen row numbers in REFERENCE_ROWS or RAW_PROPERTY_ROWS at the top of this cell.")
        return None
    selections = (*REFERENCE_ROWS, *RAW_PROPERTY_ROWS)
    if (len(set(selections)) != len(selections)
            or any(type(index) is not int or not 1 <= index <= len(candidates) for index in selections)):
        raise ValueError("Enter distinct row numbers from this cell's list.")
    fields = {candidates[index - 1]["source_field"]: tuple(
        sorted({domain["level_id"] for domain in candidates[index - 1]["target_domains"]}))
        for index in REFERENCE_ROWS}
    donor_levels = {binding["target_level_id"] for route in ROUTES.values()
                    for key, binding in route.get("joined_lookups", {}).items()
                    if key == "policy-procedures" and "target_level_id" in binding}
    if len(donor_levels) != 1:
        raise ValueError("The notebook must declare one Control Procedure target level.")
    fields[prior_field] = (next(iter(donor_levels)),)
    raw_fields = tuple(candidates[index - 1]["source_field"] for index in RAW_PROPERTY_ROWS)
    selected_targets = {domain["level_id"]: domain["module_id"]
                        for index in REFERENCE_ROWS for domain in candidates[index - 1]["target_domains"]}
    targets = _catalog_preview_targets(current, native, {level for levels in fields.values() for level in levels})
    if any(targets[level][0] != module for level, module in selected_targets.items()):
        raise ValueError("Archer module metadata changed after the inventory. Refresh the inventory before Preview.")
    return {"fields": fields, "raw": raw_fields, "targets": targets}


def install_catalog_reference_batch_preview():
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW":
        raise ValueError("Run Cells 1–4 with only the Authoritative Sources Catalog Preview selected.")
    current = contexts[0]
    route, config, plan = current["route"], current["config"], current["compiled_plan"] or {}
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native.get("guid_props")):
        raise ValueError("Use the write-disabled Catalog property baseline and rerun Cells 1–4.")

    manifest = _catalog_preview_selection(current, native)
    if manifest is None:
        return None
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


_catalog_batch_preview = install_catalog_reference_batch_preview()
if _catalog_batch_preview is not None:
    _native_catalog_apply = _catalog_batch_preview
    print("Catalog reference batch ready. Run Cells 5–7 in PREVIEW.")
