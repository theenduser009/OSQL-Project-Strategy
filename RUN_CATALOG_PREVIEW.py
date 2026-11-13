# Control Standards Catalog DEV Preview and verification.
# Paste this entire file into a new Python cell after a successful Catalog Cell 7 Preview.
# If this session already previewed all Catalog changes, this cell only prints the result.
# For a baseline session, enter selections from the displayed menus and rerun this cell.
# Then run Cell 7 once in PREVIEW and rerun this cell to print the result.

REFERENCE_ROWS = ()
RAW_PROPERTY_ROWS = ()
GUIDANCE_ROWS = ()
INSPECT_ROWS = ()

from collections import Counter, defaultdict
from decimal import Decimal
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


def install_catalog_reference_batch_preview(manifest):
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

def _handoff_catalog_reference_targets(binding):
    return binding["targets"] if "targets" in binding else [binding]


def _handoff_catalog_hierarchy_members(raw, counts):
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


def _apply_handoff_catalog_control_hierarchy(nodes, edges, target_values, context, spec, snapshots, known_levels):
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
    targets = {str(item["target_level_id"]): item for item in _handoff_catalog_reference_targets(binding["reference"])}
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
        parents = _handoff_catalog_hierarchy_members(document.get(parent_field), invalid)
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
        identifiers = _handoff_catalog_hierarchy_members(raw, counts)
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


def install_catalog_hierarchy_preview(manifest):
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
    owners = native.get("owner_bindings", native.get("declared_owner_bindings", {}))
    joined = route.get("joined_lookups", {})
    deepest = max(owners, key=lambda path: path.count("."))
    subsection_binding = owners[deepest]
    section_binding = joined[subsection_binding]["parent_binding"]
    target_configs = manifest["targets"]
    subsection_levels = [level for level, target in target_configs.items()
                         if target[1:4] == (None, None, subsection_binding)]
    section_levels = [level for level, target in target_configs.items()
                       if target[1:4] == (None, None, section_binding)]
    if len(subsection_levels) != 1 or len(section_levels) != 1:
        raise ValueError("Select the cross-reference that spans the configured Subsection and parent Section.")
    subsection_level, section_level = subsection_levels[0], section_levels[0]
    fields = [field for field, levels in manifest["fields"].items()
              if subsection_level in levels and section_level in levels]
    if len(fields) != 1 or section_level != subsection_level - 1:
        raise ValueError("Select one cross-reference that includes the Section and Subsection levels.")
    field = fields[0]
    domain = {level: target_configs[level][0] for level in manifest["fields"][field]}

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
        references = _handoff_catalog_hierarchy_members(row.get(field), {"invalid_members": 0})
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
        return _apply_handoff_catalog_control_hierarchy(
            new_nodes, new_edges, standard_values, active, spec, snapshots, known_levels)

    apply_hierarchy.catalog_hierarchy_base_apply = base_apply
    apply_hierarchy.catalog_hierarchy_base_fingerprint = base_fingerprint
    apply_hierarchy.catalog_hierarchy_fingerprint = fingerprint
    apply_hierarchy.catalog_hierarchy_snapshots = handles
    plan["mapping_fingerprint"] = fingerprint
    return apply_hierarchy

def _catalog_guidance_fields(context, native, guidance_fields, inspect_fields):
    selected_rows = (*GUIDANCE_ROWS, *INSPECT_ROWS)
    if guidance_fields:
        if selected_rows:
            raise ValueError("Choose field names or row numbers for the guidance preview.")
        return guidance_fields, inspect_fields
    if inspect_fields:
        raise ValueError("Enter the guidance fields or choose guidance row numbers.")
    lookup = SOURCE_INPUTS[context["source_key"]]["lookups_by_model"]["CATALOG"]
    metadata = lookup["native_control_guid_metadata"][native["lookup"]]
    keys = {
        row["SQL_FIELD_NAME"] for row in metadata.to_local_iterator()
        if row["LEVEL_ID"] == native["guid_props"]["level_id"]
        and isinstance(row["SQL_FIELD_NAME"], str)
        and re.fullmatch(r"[A-Z][A-Z0-9_]*", row["SQL_FIELD_NAME"])
    }
    terms = re.compile(r"GUIDANCE|GUIDELINES?|REQUIREMENTS?|DESCRIPTION|SUMMARY|STATEMENTS?|PARAMETERS?")
    names = sorted(field for field in keys if terms.search(field)
                   and field != native["fields"]["parts"])
    if not names:
        raise ValueError("Archer metadata returned no Catalog guidance or inspection candidates.")
    if not selected_rows:
        for index, field in enumerate(names, 1):
            print(f"{index:>3}  {field}")
        print("Enter the numbers in GUIDANCE_ROWS and INSPECT_ROWS, then rerun this cell.")
        return (), ()
    if (not GUIDANCE_ROWS or len(set(selected_rows)) != len(selected_rows)
            or any(type(index) is not int or not 1 <= index <= len(names) for index in selected_rows)):
        raise ValueError("Choose distinct numbers from the displayed list and include guidance rows.")
    return (tuple(names[index - 1] for index in GUIDANCE_ROWS),
            tuple(names[index - 1] for index in INSPECT_ROWS))


def install_catalog_guidance_preview(guidance_fields, inspect_fields):
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW":
        raise ValueError("Select only the write-disabled Catalog route in PREVIEW.")
    context = contexts[0]
    route, config, plan = context["route"], context["config"], context["compiled_plan"]
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native.get("guid_props")):
        raise ValueError("Use the write-disabled native Catalog route.")
    if native.get("extra_parts"):
        raise ValueError("The installed Catalog mapping already defines additional Parts. Run its normal Preview.")
    guidance_fields, inspect_fields = _catalog_guidance_fields(context, native, guidance_fields, inspect_fields)
    if not guidance_fields:
        return None
    fields = (*guidance_fields, *inspect_fields)
    if (len(set(fields)) != len(fields)
            or any(not isinstance(field, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", field)
                   for field in fields)
            or native["fields"]["parts"] in guidance_fields):
        raise ValueError("Use distinct source field keys and keep the existing statement.")
    guidance = tuple(sorted(guidance_fields))
    inspections = tuple(sorted(inspect_fields))
    classes = {field: field.lower().replace("_", "-") for field in guidance}
    if len(set(classes.values())) != len(classes):
        raise ValueError("Guidance fields have conflicting part classes.")

    base_apply = _native_catalog_apply
    base_fingerprint = plan["mapping_fingerprint"]
    if getattr(base_apply, "catalog_guidance_fingerprint", None) == base_fingerprint:
        base_fingerprint = base_apply.catalog_guidance_base_fingerprint
        base_apply = base_apply.catalog_guidance_base_apply
    reference_apply = base_apply
    if getattr(base_apply, "catalog_hierarchy_fingerprint", None) == base_fingerprint:
        reference_apply = base_apply.catalog_hierarchy_base_apply
        if getattr(reference_apply, "catalog_guidance_base_apply", None):
            print("Catalog guidance is already active under the hierarchy. Run Cell 7 in PREVIEW.")
            return None
    if not (getattr(reference_apply, "catalog_reference_batch_base_apply", None)
            or any(prop.get("transform") == "catalog-record-reference" for prop in native.get("extra_props", ()))):
        raise ValueError("Use the same session as the Catalog reference or hierarchy Preview.")

    fingerprint = hashlib.sha256(json.dumps(
        [base_fingerprint, "catalog-guidance-preview-v1", guidance, inspections],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()

    def apply_guidance(nodes, edges, source_df, active):
        config = active["config"]
        active_plan = active["compiled_plan"]
        if (config.get("WRITE_ALLOWED") is not False or config.get("EXECUTE_WRITES") is not False
                or active_plan.get("mapping_fingerprint") != fingerprint):
            raise ValueError("Run the guidance helper in the selected write-disabled Preview.")
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

        controls = [node for node in new_nodes if node["ELEMENT_PATH"] in native["paths"]]
        control_ids = {node["INSTANCE_KEY"] for node in controls}
        source = active["lookups"]["native_control_sources"][native["lookup"]]
        values = {}
        for row in source.to_local_iterator():
            record_id = _source_id(row["SOURCE_RECORD_ID"])
            if record_id in control_ids:
                if record_id in values:
                    raise ValueError("Duplicate Control Standard in frozen Catalog input.")
                values[record_id] = _metadata_parse(row, active)
        if control_ids != values.keys():
            raise ValueError("A Catalog control is missing from the frozen input.")

        counts = {field: dict(missing=0, null=0, blank=0, non_text=0, emitted=0)
                  for field in guidance}
        shapes = {field: Counter() for field in inspections}
        for doc in values.values():
            statement = doc.get(native["fields"]["parts"])
            has_statement = isinstance(statement, str) and bool(statement.strip())
            for field in inspections:
                value = doc.get(field)
                if field not in doc:
                    shape = "missing"
                elif value is None:
                    shape = "null"
                elif isinstance(value, str):
                    shape = "text" if value.strip() else "blank"
                elif isinstance(value, (dict, list)):
                    shape = type(value).__name__ if value else "empty_" + type(value).__name__
                else:
                    shape = type(value).__name__
                shapes[field][shape] += 1
                if shape == "text" and not has_statement:
                    shapes[field]["text_where_statement_empty"] += 1

        for node in controls:
            doc = values[node["INSTANCE_KEY"]]
            parts = []
            for field in guidance:
                value = doc.get(field)
                if field not in doc:
                    outcome = "missing"
                elif value is None:
                    outcome = "null"
                elif not isinstance(value, str):
                    outcome = "non_text"
                elif not value.strip():
                    outcome = "blank"
                else:
                    outcome = "emitted"
                    parts.append({"name": "guidance", "class": classes[field], "prose": value})
                counts[field][outcome] += 1
            if parts:
                payload = json.loads(node["METADATA_JSON"])
                existing = payload.setdefault("parts", [])
                identities = {(part["name"], part.get("class")) for part in existing}
                if any((part["name"], part["class"]) in identities for part in parts):
                    raise ValueError("A guidance part already exists on this Catalog control.")
                existing.extend(parts)
                node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)

        report = active["graph_report"]
        if guidance:
            report["NATIVE_CATALOG_GUIDANCE_PARTS"] = counts
        if inspections:
            report["NATIVE_CATALOG_PARTS_INPUT_SHAPES"] = {field: dict(shape) for field, shape in shapes.items()}
        return new_nodes, new_edges

    apply_guidance.catalog_guidance_base_apply = base_apply
    apply_guidance.catalog_guidance_base_fingerprint = base_fingerprint
    apply_guidance.catalog_guidance_fingerprint = fingerprint
    plan["mapping_fingerprint"] = fingerprint
    return apply_guidance

def install_catalog_statement_preview(inspected_fields):
    report = globals().get("PIPELINE_REPORT") or {}
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if (len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW"
            or report.get("status") != "PREVIEW_COMPLETE"
            or report.get("writes_executed") is not False):
        raise ValueError("Use the same session as the completed write-disabled Catalog Guidance Preview.")
    context = contexts[0]
    route, config, plan = context["route"], context["config"], context["compiled_plan"]
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native.get("guid_props")):
        raise ValueError("Use the write-disabled native Catalog route.")
    if any(part.get("part_name") == "statement" for part in native.get("extra_parts", ())):
        raise ValueError("The installed mapping already defines statement Parts. Run its normal Preview.")
    primary = native["fields"]["parts"]
    fields = tuple(sorted(field for field in inspected_fields if field.endswith("_STATEMENT") and field != primary))
    if not fields or any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", field) for field in fields):
        raise ValueError("The Guidance Preview did not report the selected statement fields.")
    namespace = "urn:archer:source:v1"
    classes = {field: field.lower().replace("_", "-") for field in fields}

    base_apply = _native_catalog_apply
    base_fingerprint = plan["mapping_fingerprint"]
    if getattr(base_apply, "catalog_statement_fingerprint", None) == base_fingerprint:
        base_fingerprint = base_apply.catalog_statement_base_fingerprint
        base_apply = base_apply.catalog_statement_base_apply
    if not (getattr(base_apply, "catalog_guidance_base_apply", None)
            or getattr(base_apply, "catalog_hierarchy_base_apply", None)):
        raise ValueError("The Guidance Preview helper must still be active.")
    fingerprint = hashlib.sha256(json.dumps(
        [base_fingerprint, "catalog-statement-preview-v1", fields],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()

    def apply_statements(nodes, edges, source_df, active):
        active_plan = active["compiled_plan"]
        if (active["config"].get("WRITE_ALLOWED") is not False
                or active["config"].get("EXECUTE_WRITES") is not False
                or active_plan.get("mapping_fingerprint") != fingerprint):
            raise ValueError("Use the selected write-disabled Catalog Preview.")
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

        paths = set(native["paths"])
        controls = [node for node in new_nodes if node["ELEMENT_PATH"] in paths]
        owners = {node["INSTANCE_KEY"] for node in controls}
        source = active["lookups"]["native_control_sources"][native["lookup"]]
        documents = {}
        for row in source.to_local_iterator():
            identifier = _source_id(row["SOURCE_RECORD_ID"])
            if identifier in owners:
                if identifier in documents:
                    raise ValueError("Duplicate Control Standard in frozen Catalog input.")
                documents[identifier] = _metadata_parse(row, active)
        if documents.keys() != owners:
            raise ValueError("A Catalog control is missing from the frozen input.")

        counts = {field: dict(missing=0, null=0, blank=0, non_text=0, emitted=0)
                  for field in fields}
        missing_primary = set()
        with_alternates = set()
        placements_without_primary = 0
        placements_without_any_statement = 0
        for node in controls:
            owner = node["INSTANCE_KEY"]
            document = documents[owner]
            payload = json.loads(node["METADATA_JSON"])
            existing = payload.get("parts", [])
            has_primary = any(part.get("name") == "statement" and not part.get("class")
                              and not part.get("ns") and isinstance(part.get("prose"), str)
                              and part["prose"].strip() for part in existing)
            extras = []
            for field in fields:
                value = document.get(field)
                if field not in document:
                    shape = "missing"
                elif value is None:
                    shape = "null"
                elif not isinstance(value, str):
                    shape = "non_text"
                elif not value.strip():
                    shape = "blank"
                else:
                    shape = "emitted"
                    extras.append(dict(name="statement", ns=namespace, **{"class": classes[field]}, prose=value))
                counts[field][shape] += 1
            if not has_primary:
                missing_primary.add(owner)
                placements_without_primary += 1
                if extras:
                    with_alternates.add(owner)
                else:
                    placements_without_any_statement += 1
            if not extras:
                continue
            identities = {(part.get("name"), part.get("class"), part.get("ns")) for part in existing}
            if any((part["name"], part["class"], part["ns"]) in identities for part in extras):
                raise ValueError("A source-labeled statement Part already exists on this control.")
            payload["parts"] = [*existing, *extras]
            node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)

        active["graph_report"]["NATIVE_CATALOG_STATEMENT_PARTS"] = counts
        active["graph_report"]["NATIVE_CATALOG_STATEMENT_COVERAGE"] = {
            "distinct_standards_without_primary": len(missing_primary),
            "distinct_standards_without_primary_with_alternate": len(with_alternates),
            "placements_without_primary": placements_without_primary,
            "placements_without_any_statement": placements_without_any_statement,
        }
        return new_nodes, new_edges

    apply_statements.catalog_statement_base_apply = base_apply
    apply_statements.catalog_statement_base_fingerprint = base_fingerprint
    apply_statements.catalog_statement_fingerprint = fingerprint
    plan["mapping_fingerprint"] = fingerprint
    return apply_statements

def catalog_preview_result():
    report = globals().get("PIPELINE_REPORT") or {}
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if (len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW"
            or report.get("status") != "PREVIEW_COMPLETE"
            or report.get("writes_executed") is not False
            or report.get("commit_attempted") is not False):
        raise ValueError("Use the same session as a completed, write-disabled Catalog Cell 7 Preview.")
    context = contexts[0]
    key = (context["source_key"], "CATALOG")
    config, plan = context["config"], context["compiled_plan"]
    native = plan.get("native_catalog") or {}
    groups = [group for group in report.get("groups", [])
              if (group.get("source"), group.get("model")) == key]
    graph = (globals().get("MODEL_GRAPHS") or {}).get(key)
    if (len(groups) != 1 or not graph or not native or config.get("OSCAL_MODEL") != "CATALOG"
            or config.get("WRITE_ALLOWED") is not False or config.get("EXECUTE_WRITES") is not False
            or context["route"].get("write_allowed") is not False):
        raise ValueError("Select only the write-disabled Control Standards Catalog route.")
    group = groups[0]
    load = group["load"]
    if (load.get("status") != "PREVIEW_PASSED_NO_TARGET_DML"
            or any(load.get(key) is not True for key in ("validation_passed", "pre_write_validation_passed", "storage_verified"))
            or any(load.get(key) is not False for key in ("writes_executed", "persisted", "committed", "target_dml_attempted"))):
        raise ValueError("The completed Catalog Preview did not pass its validation and no-write checks.")
    graph_plan = graph["context"]["compiled_plan"]
    if graph_plan.get("mapping_fingerprint") != group.get("mapping_fingerprint"):
        raise ValueError("The Catalog graph and Preview report do not match.")
    native_report = group.get("native_catalog", {})
    return context, native, graph_plan["native_catalog"], load, native_report


def run_catalog_handoff():
    global _native_catalog_apply
    context, native, graph_native, load, report = catalog_preview_result()
    required = (
        "NATIVE_CATALOG_RECORD_REFERENCES", "NATIVE_CATALOG_CONTROL_HIERARCHY",
        "NATIVE_CATALOG_GUIDANCE_PARTS", "NATIVE_CATALOG_STATEMENT_PARTS",
        "NATIVE_CATALOG_STATEMENT_COVERAGE",
    )
    if all(report.get(key) for key in required):
        counts = report["NATIVE_CATALOG_STATEMENT_PARTS"]
        coverage = report["NATIVE_CATALOG_STATEMENT_COVERAGE"]
        changes = load.get("expected_changes", {})
        facts = changes.get("F", {})
        is_installed = (
            bool(graph_native.get("control_hierarchy_reference"))
            and {part["source_field"] for part in graph_native.get("extra_parts", ())
                 if part.get("part_name") == "statement"} == counts.keys()
        )
        if (len(counts) != 3 or facts.get("INSERTS") != 0 or facts.get("UPDATES") != 0
                or any(value.get("emitted", 0) <= 0 or value.get("non_text") != 0 for value in counts.values())):
            raise ValueError("Review the Statement Parts and FACT counts in Cell 7.")
        hierarchy = tuple(report["NATIVE_CATALOG_CONTROL_HIERARCHY"].values())
        print(json.dumps({
            "status": "CATALOG_PREVIEW_VERIFIED",
            "installation": "compiled mapping" if is_installed else "notebook preview helpers",
            "statement_parts": sum(value["emitted"] for value in counts.values()),
            "guidance_parts": sum(value["emitted"] for value in report["NATIVE_CATALOG_GUIDANCE_PARTS"].values()),
            "placements_without_primary_statement": coverage["placements_without_primary"],
            "placements_without_any_statement": coverage["placements_without_any_statement"],
            "resolved_subsection_references": sum(value["resolved_subsections"] for value in hierarchy),
            "resolved_section_references": sum(value["resolved_sections"] for value in hierarchy),
            "missing_subsection_references": sum(value["missing_subsections"] for value in hierarchy),
            "fact_rows_unchanged": facts["UNCHANGED"],
            "target_writes": False,
        }, indent=2))
        return

    plan = context["compiled_plan"]
    if (native.get("extra_parts") or native.get("control_hierarchy_reference")
            or any(prop.get("transform") == "catalog-record-reference" for prop in native.get("extra_props", ()))):
        raise ValueError("Use Cell 7 with the installed Catalog files and review the missing report fields.")
    if getattr(_native_catalog_apply, "catalog_combined_handoff_active", False):
        print("Run Cell 7 in PREVIEW to verify the prepared Catalog changes.")
        return
    if any(getattr(_native_catalog_apply, marker, None) for marker in (
            "catalog_reference_batch_base_apply", "catalog_hierarchy_base_apply",
            "catalog_guidance_base_apply", "catalog_statement_base_apply")):
        raise ValueError("Use either the completed overlay run or a fresh baseline session for this combined cell.")

    manifest = _catalog_preview_selection(context, native)
    guidance, inspections = _catalog_guidance_fields(context, native, (), ())
    if manifest is None or not guidance:
        return
    if any(field in guidance for field in inspections) or len([f for f in inspections if f.endswith("_STATEMENT")]) != 3:
        raise ValueError("Select three distinct alternate statement fields for inspection.")
    original = _native_catalog_apply
    saved_plan = dict(plan)
    try:
        _native_catalog_apply = install_catalog_reference_batch_preview(manifest)
        _native_catalog_apply = install_catalog_hierarchy_preview(manifest)
        _native_catalog_apply = install_catalog_guidance_preview((), ())
        _native_catalog_apply = install_catalog_statement_preview(inspections)
        _native_catalog_apply.catalog_combined_handoff_active = True
    except Exception:
        _native_catalog_apply = original
        plan.clear()
        plan.update(saved_plan)
        raise
    print("Catalog Preview ready. Run Cell 7 once in PREVIEW, then rerun this cell for the summary.")


run_catalog_handoff()
