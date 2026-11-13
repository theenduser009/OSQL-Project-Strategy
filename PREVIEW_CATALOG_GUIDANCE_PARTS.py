# Run after the Catalog reference helper and before running Cells 5–7 in PREVIEW.
# Enter the exact source field keys to map as guidance or inspect in the same run.
# Existing reference selections remain active in the same session.

GUIDANCE_FIELDS = ()
INSPECT_FIELDS = ()

from collections import Counter
import hashlib
import json
import re


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
    if not guidance_fields:
        raise ValueError("Enter the guidance field keys in GUIDANCE_FIELDS at the top of this cell.")
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
    if not (getattr(base_apply, "catalog_reference_batch_base_apply", None)
            or any(prop.get("transform") == "catalog-record-reference" for prop in native.get("extra_props", ()))):
        raise ValueError("Run the Catalog reference helper first, then rerun this cell.")

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


_catalog_guidance_preview = install_catalog_guidance_preview(GUIDANCE_FIELDS, INSPECT_FIELDS)
if _catalog_guidance_preview is not None:
    _native_catalog_apply = _catalog_guidance_preview
    print("Catalog guidance ready. Run Cells 5–7 in PREVIEW.")
