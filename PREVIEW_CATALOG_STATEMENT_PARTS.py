# Paste into a new Python cell in the same session as the completed Guidance Preview.
# Run this cell as-is, then rerun only Cell 7 in PREVIEW.

import hashlib
import json
import re


def install_catalog_statement_preview():
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
    groups = [group for group in report.get("groups", [])
              if (group.get("source"), group.get("model")) == (context["source_key"], "CATALOG")]
    if len(groups) != 1:
        raise ValueError("Use the completed Guidance Preview for this Catalog route.")
    inspected = groups[0].get("native_catalog", {}).get("NATIVE_CATALOG_PARTS_INPUT_SHAPES", {})
    primary = native["fields"]["parts"]
    fields = tuple(sorted(field for field in inspected if field.endswith("_STATEMENT") and field != primary))
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


_native_catalog_apply = install_catalog_statement_preview()
print("Catalog statements ready. Run Cell 7 in PREVIEW.")
