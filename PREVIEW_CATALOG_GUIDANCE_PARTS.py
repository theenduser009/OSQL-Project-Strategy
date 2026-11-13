# Run after the Catalog reference or hierarchy Preview, then rerun only Cell 7 in PREVIEW.
# If the field settings are empty, run once to see numbered choices from Archer metadata.
# The existing reference and hierarchy work is reused in the same session.

GUIDANCE_FIELDS = ()
INSPECT_FIELDS = ()
GUIDANCE_ROWS = ()
INSPECT_ROWS = ()

from collections import Counter
import hashlib
import json
import re


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


_catalog_guidance_preview = install_catalog_guidance_preview(GUIDANCE_FIELDS, INSPECT_FIELDS)
if _catalog_guidance_preview is not None:
    _native_catalog_apply = _catalog_guidance_preview
    print("Catalog guidance ready. Run Cell 7 in PREVIEW.")
