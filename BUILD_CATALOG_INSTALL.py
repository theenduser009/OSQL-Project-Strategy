# Run this cell in the same Snowflake DEV session as the completed Statement Preview.
# It builds the install CSV and JSON from that run and the notebook's existing files.

import csv
from io import BytesIO, StringIO
import inspect
import json
import os
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile


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


def _catalog_install_route_columns(target, base_control, has_join):
    return {
        "source_table": target["source_table"],
        "content_id_column": target.get("source_id_column", target.get("content_id_column", "CONTENT_ID")),
        "json_column": target.get("source_json_column", target.get("json_column", "CURATED_JSON")),
        "order_candidates": list(target.get("source_order", target.get(
            "order_candidates", base_control.get("order_candidates", ()) if has_join else ()))),
    }


def _catalog_completed_selections(report):
    reference_report = report.get("NATIVE_CATALOG_RECORD_REFERENCES", {})
    guidance = tuple(report.get("NATIVE_CATALOG_GUIDANCE_PARTS", {}))
    statements = tuple(report.get("NATIVE_CATALOG_STATEMENT_PARTS", {}))
    hierarchy = report.get("NATIVE_CATALOG_CONTROL_HIERARCHY", {})
    if len(reference_report) != 8 or len(guidance) != 7 or len(statements) != 3 or len(hierarchy) != 1:
        raise ValueError("Open the same notebook session as the complete Catalog Statement Preview.")
    current = _native_catalog_apply
    visited = set()
    while current not in visited:
        visited.add(current)
        if getattr(current, "catalog_reference_batch_base_apply", None):
            references = inspect.getclosurevars(current).nonlocals
            fields, raw = references.get("fields", {}), references.get("raw_fields", ())
            if fields.keys() != reference_report.keys() or len(raw) != 1:
                raise ValueError("Catalog field selections differ from the completed Preview.")
            hierarchy_field = next(iter(hierarchy))
            if hierarchy_field not in fields:
                raise ValueError("The completed hierarchy field is absent from the reference selections.")
            names = (*fields, *raw, *guidance, *statements)
            if len(set(names)) != len(names) or any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", field) for field in names):
                raise ValueError("The completed Catalog Preview selections conflict.")
            return fields, raw, guidance, statements, hierarchy_field
        parent = next((getattr(current, key, None) for key in (
            "catalog_statement_base_apply", "catalog_guidance_base_apply", "catalog_hierarchy_base_apply",
        ) if getattr(current, key, None)), None)
        if parent is None:
            break
        current = parent
    raise ValueError("The active notebook session does not have the completed reference helper selections.")


def _catalog_install_config(document, context, native, fields, hierarchy_field):
    route_key = (context["source_key"], "CATALOG")
    matches = [route for route in document["routes"]
               if (route.get("source_key"), route.get("model")) == route_key]
    if len(matches) != 1:
        raise ValueError("The routes file has no unique Control Standards Catalog route.")
    destination = matches[0]
    active = context["route"]
    for key in ("source_table", "target_dim", "target_fact", "native_controls", "joined_lookups"):
        if destination.get(key) != active.get(key):
            raise ValueError("The local routes file changed since the Preview. Restore the matching files.")
    if destination.get("write_allowed") is not False:
        raise ValueError("The Catalog route must be write-disabled.")
    document["run"] = {**document["run"], "source_keys": [route_key[0]], "models": [route_key[1]], "mode": "PREVIEW"}

    native_contracts = destination["native_controls"]
    lookup = native["lookup"]
    control = native_contracts[lookup]
    if control.get("control_hierarchy_reference") or control.get("reference_properties"):
        raise ValueError("Start with the baseline routes file used for the completed overlay Preview.")
    levels = {level for target_levels in fields.values() for level in target_levels}
    targets = _catalog_preview_targets(context, native, levels)
    target_bindings = {}
    projected = {}
    for level in sorted(levels):
        module, source_key, model, joined_key, title = targets[level]
        source_route = active if source_key is None else ROUTES[(source_key, model)]
        if joined_key == "native":
            key = lookup
        else:
            source = source_route["joined_lookups"][joined_key] if joined_key else source_route
            key = "catalog-reference-level-" + str(level)
            if key in native_contracts:
                raise ValueError("A generated Catalog target lookup already exists.")
            native_contracts[key] = _catalog_install_route_columns(source, control, joined_key is not None)
        target_bindings[level] = dict(lookup_key=key, target_level_id=level, target_module_id=module,
                                      display_name_field=title)
        projected[level] = (source_key, model, joined_key)

    owner_paths = native.get("owner_bindings", native.get("declared_owner_bindings", {}))
    deepest_path = max(owner_paths, key=lambda path: path.count("."))
    subsection_lookup = owner_paths[deepest_path]
    section_lookup = destination["joined_lookups"][subsection_lookup]["parent_binding"]
    subsection_levels = [level for level in fields[hierarchy_field]
                         if projected[level] == (None, None, subsection_lookup)]
    section_levels = [level for level in fields[hierarchy_field]
                      if projected[level] == (None, None, section_lookup)]
    if len(subsection_levels) != 1 or section_levels != [subsection_levels[0] - 1]:
        raise ValueError("The selected Catalog hierarchy does not match the installed parent lookup.")

    transport = SOURCE_INPUTS[route_key[0]]["lookups_by_model"]["CATALOG"]
    metadata = transport["native_control_guid_metadata"][lookup]
    field_ids = [int(row["FIELD_ID"]) for row in metadata.to_local_iterator()
                 if row["LEVEL_ID"] == native["guid_props"]["level_id"] and row["SQL_FIELD_NAME"] == hierarchy_field]
    if len(field_ids) != 1 or field_ids[0] <= 0:
        raise ValueError("The installed Archer hierarchy field has no unique identity.")
    control["control_hierarchy_reference"] = {
        "source_field": hierarchy_field, "field_id": field_ids[0], "subsection_lookup": subsection_lookup,
        "section_lookup": section_lookup, "target_level_id": subsection_levels[0],
    }
    control["reference_properties"] = {
        field: {"targets": [target_bindings[level] for level in field_levels]}
        for field, field_levels in fields.items()
    }
    return document


def _catalog_install_mapping(csv_text, context, native, fields, raw, guidance, statements):
    reader = csv.DictReader(StringIO(csv_text, newline=""), strict=True)
    rows = list(reader)
    columns = reader.fieldnames or []
    columns_by_name = {name.strip().upper(): name for name in columns}
    if not rows or len(columns_by_name) != len(columns) or any(None in row for row in rows):
        raise ValueError("The installed mapping CSV is missing or malformed.")
    if len(native["paths"]) != 4:
        raise ValueError("Expected the four Catalog control placement paths.")
    namespace = "urn:archer:source:v1"
    declarations = (
        (fields, "props", "catalog-record-reference", None, namespace, "Extension Property", "catalog-reference"),
        (raw, "props", "json-value", None, namespace, "Extension Property", "catalog-property"),
        (guidance, "parts", "prose-direct", "guidance", "", "Direct/Transform", "catalog-guidance"),
        (statements, "parts", "prose-direct", "statement", namespace, "Direct", "catalog-optional-statement"),
    )
    seen = {row.get(columns_by_name["RULE_ID"]) for row in rows}
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    for names, suffix, transform, part_name, ns, kind, recipe in declarations:
        for field in names:
            for position, path in enumerate(sorted(native["paths"]), 1):
                rule = f"control-standard:{recipe}:{position}:{field}"
                if rule in seen:
                    raise ValueError("A generated Catalog rule already exists. Use the baseline CSV.")
                seen.add(rule)
                new_row = dict(
                    SOURCE_FIELD_NAME=field, OSCAL_MODEL="Catalog", OSCAL_ELEMENT_PATH=f"{path}.{suffix}",
                    EXECUTION_STATUS="APPROVED", TRANSFORM_ID=transform, SOURCE_KEY=context["source_key"],
                    NULL_POLICY="omit", LINEAGE_REQUIRED="N", VALUE_SOURCE="FIELD", LOOKUP_KEY=native["lookup"],
                    PROPERTY_NAME=part_name or field.lower().replace("_", "-"), MAPPING_TYPE=kind,
                    PROPERTY_NAMESPACE=ns, RULE_ID=rule,
                )
                writer.writerow({columns_by_name[key]: value for key, value in new_row.items()})
    added = len(native["paths"]) * sum(len(declaration[0]) for declaration in declarations)
    return csv_text.rstrip("\r\n") + "\n" + output.getvalue(), len(rows), added


def build_catalog_install():
    context, native, _, _, report = catalog_preview_result()
    fields, raw, guidance, statements, hierarchy_field = _catalog_completed_selections(report)
    routes_path = Path(ROUTES_CONFIG_FILE)
    mapping_path = Path(MAPPING_FILE)
    routes = json.loads(routes_path.read_text(encoding="utf-8-sig"))
    installed = _catalog_install_config(routes, context, native, fields, hierarchy_field)
    mapping_text, original, added = _catalog_install_mapping(
        mapping_path.read_text(encoding=context["route"].get("csv_encoding", "utf-8-sig")),
        context, native, fields, raw, guidance, statements,
    )
    # Keep configured filenames. The notebook will load these after you replace its input files.
    mapping_name, routes_name = mapping_path.name, routes_path.name
    structure = installed["files"]["structure"]
    routes_text = json.dumps(installed, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(mapping_name, mapping_text)
        bundle.writestr(routes_name, routes_text)
    package = output.getvalue()
    directory = Path.cwd() if os.access(Path.cwd(), os.W_OK) else Path("/tmp")
    package_path = directory / "catalog-install-inputs.zip"
    package_path.write_bytes(package)
    for name, contents in ((mapping_name, mapping_text), (routes_name, routes_text)):
        (directory / ("catalog-install-" + name)).write_text(contents, encoding="utf-8")
    print(f"Ready: {mapping_name}, {routes_name}. {original} existing rules + {added} new rules. "
          "Keep the existing registry file:", structure)
    try:
        import streamlit as st
        st.download_button("Download Catalog mapping and routes", data=package,
                           file_name=package_path.name, mime="application/zip")
    except (ImportError, AttributeError):
        pass
    print("Session file:", package_path)
    return package


CATALOG_INSTALL_INPUTS = build_catalog_install()

