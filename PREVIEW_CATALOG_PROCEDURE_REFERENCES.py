# Snowflake notebook. Run Cells 1–4 on the existing Catalog property baseline.
# Paste this into a new Python cell after Cell 4. Then run Cells 5–7 in PREVIEW.
#
# This temporary Preview reads the installed routes and uses the mapper's
# existing write guard.

import hashlib
import json


def install_catalog_procedure_reference_preview():
    contexts = globals().get("MAPPING_CONTEXTS") or []
    if len(contexts) != 1:
        raise ValueError("Run Cells 1–4 with only the Authoritative Sources Catalog Preview selected.")
    current = contexts[0]
    route = current["route"]
    config = current["config"]
    plan = current["compiled_plan"] or {}
    native = plan.get("native_catalog") or {}
    if (config.get("OSCAL_MODEL") != "CATALOG"
            or config.get("EXECUTE_WRITES") is not False
            or config.get("WRITE_ALLOWED") is not False
            or route.get("write_allowed") is not False
            or not native.get("guid_props")):
        raise ValueError("Use the write-disabled Catalog property baseline and rerun Cells 1–4.")

    source_field = native["guid_props"]["source_field"]
    prop_name = source_field.lower().replace("_", "-")
    namespace = "urn:archer:source:v1"
    if any(prop["property_name"] == prop_name and prop["namespace"] == namespace
           for prop in native.get("extra_props", ())):
        raise ValueError("The installed mapping already has the procedure reference property.")
    later_properties = {
        (prop["property_name"], prop["namespace"], prop.get("class"))
        for prop in native.get("extra_props", ())
        if prop["source_field"] > source_field
    }

    procedure_bindings = [candidate
                          for available_route in ROUTES.values()
                          for key, candidate in available_route.get("joined_lookups", {}).items()
                          if key == "policy-procedures"]
    procedure_domains = {(binding["source_table"], binding["target_level_id"])
                         for binding in procedure_bindings}
    if len(procedure_domains) != 1:
        raise ValueError("The installed routes must declare one Control Procedure target domain.")
    target_table, target_level = next(iter(procedure_domains))
    standard_lookup = native["lookup"]
    standard_input = route["native_controls"][standard_lookup]
    metadata_binding = route["native_control_guid_properties"][standard_lookup]
    metadata = _input_table(session, metadata_binding["metadata_table"])
    metadata_names = _normalized_columns(metadata.columns)
    level_column = _input_column(metadata_names, metadata_binding["level_id_column"])
    module_column = _input_column(metadata_names, "MODULE_ID")
    if level_column is None or module_column is None:
        raise ValueError("The configured Archer field metadata needs level and module columns.")
    modules = (metadata.filter((col(level_column) == lit(target_level)) & col(module_column).is_not_null())
               .select(col(module_column).alias("MODULE_ID"))
               .distinct().collect())
    if len(modules) != 1 or modules[0]["MODULE_ID"] is None:
        raise ValueError("The Procedure level did not resolve to one Archer module.")
    target_module = int(_source_id(str(modules[0]["MODULE_ID"])))

    target_frame, _, _ = load_source_input(session, {
        "source_table": target_table,
        "source_id_column": standard_input.get("content_id_column", "CONTENT_ID"),
        "source_json_column": standard_input.get("json_column", "CURATED_JSON"),
        "source_order": standard_input.get("order_candidates", ()),
    })
    target_names = {}
    for record in target_frame.to_local_iterator():
        content_id = _source_id(record["SOURCE_RECORD_ID"])
        if content_id in target_names:
            raise ValueError("The Procedure target snapshot has a duplicate Content ID.")
        name = _metadata_parse(record, current).get("CONTROL_PROCEDURE_NAME")
        target_names[content_id] = name if isinstance(name, str) and name.strip() else None

    baseline_fingerprint = plan.get("procedure_reference_preview_base", plan["mapping_fingerprint"])
    fingerprint = hashlib.sha256(json.dumps(
        [baseline_fingerprint, "procedure-reference-preview-v1", source_field, prop_name,
         target_table, target_level, target_module],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    base_apply = getattr(_native_catalog_apply, "procedure_reference_preview_base", _native_catalog_apply)

    def apply_procedure_reference_preview(nodes, edges, source_df, context):
        current_config = context["config"]
        if (current_config.get("WRITE_ALLOWED") is not False
                or current_config.get("EXECUTE_WRITES") is not False
                or context["compiled_plan"].get("mapping_fingerprint") != fingerprint):
            raise ValueError("Rerun the procedure-reference cell for the selected write-disabled Preview.")
        result_nodes, result_edges = base_apply(nodes, edges, source_df, context)
        controls = [(node, json.loads(node["METADATA_JSON"])) for node in result_nodes
                    if node["ELEMENT_PATH"] in native["paths"]]
        counts = dict(references=0, resolved=0, invalid_members=0, missing_targets=0, missing_names=0)
        control_ids = {node["INSTANCE_KEY"] for node, _ in controls}
        resolved = {}
        standard_frame = context["lookups"]["native_control_sources"][standard_lookup]
        for record in standard_frame.to_local_iterator():
            control_id = _source_id(record["SOURCE_RECORD_ID"])
            if control_id not in control_ids:
                continue
            raw = _metadata_parse(record, context).get(source_field)
            members = raw if isinstance(raw, list) else [] if raw is None else [raw]
            target_ids = set()
            for member in members:
                identifier = member.get("ContentId") if isinstance(member, dict) else member
                try:
                    content_id = _source_id(identifier)
                except CatalogControlError:
                    counts["invalid_members"] += 1
                    continue
                if isinstance(member, dict) and any(
                        member.get(key) is not None and str(member[key]) != str(expected)
                        for key, expected in (("LevelId", target_level), ("ModuleId", target_module))):
                    counts["invalid_members"] += 1
                    continue
                target_ids.add(content_id)
            counts["references"] += len(target_ids)
            values = []
            for content_id in sorted(target_ids, key=int):
                if content_id not in target_names:
                    counts["missing_targets"] += 1
                elif target_names[content_id] is None:
                    counts["missing_names"] += 1
                else:
                    values.append({"ContentId": int(content_id), "ModuleId": target_module,
                                   "Name": target_names[content_id]})
            counts["resolved"] += len(values)
            resolved[control_id] = values
        if set(resolved) != control_ids:
            raise ValueError("A Catalog control was missing from the frozen Control Standards input.")

        occurrences = 0
        for node, payload in controls:
            values = resolved[node["INSTANCE_KEY"]]
            if values:
                properties = payload["props"]
                index = next((i for i, prop in enumerate(properties)
                              if (prop["name"], prop.get("ns"), prop.get("class")) in later_properties),
                             len(properties))
                properties.insert(index, {"name": prop_name, "ns": namespace,
                                          "value": _metadata_json_text(values)})
                node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
                occurrences += 1
        report = context["graph_report"]
        report["NATIVE_CATALOG_EXTRA_PROP_OCCURRENCES"] = (
            report.get("NATIVE_CATALOG_EXTRA_PROP_OCCURRENCES", 0) + occurrences)
        report["NATIVE_CATALOG_RECORD_REFERENCES"] = {source_field: counts}
        return result_nodes, result_edges

    apply_procedure_reference_preview.procedure_reference_preview_base = base_apply
    plan["procedure_reference_preview_base"] = baseline_fingerprint
    plan["mapping_fingerprint"] = fingerprint
    return apply_procedure_reference_preview


_native_catalog_apply = install_catalog_procedure_reference_preview()
print("Catalog Procedure reference Preview ready. Run Cells 5–7 in PREVIEW.")
