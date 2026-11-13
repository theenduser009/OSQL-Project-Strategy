# In the notebook with a completed Catalog hierarchy Preview, run this Python
# cell, then run Cell 7 in PREVIEW. Review NATIVE_CATALOG_CONTROL_GROUP_LINKS.

from collections import Counter, defaultdict
import hashlib
import json
from urllib.parse import quote


def _add_catalog_control_group_links(nodes, control_paths, target_paths):
    """Use verified source references and actual OSCAL IDs in each Catalog."""
    roots = Counter(node["SOURCE_RECORD_ID"] for node in nodes if node["ELEMENT_PATH"] == "catalog")
    if any(count != 1 for count in roots.values()):
        raise ValueError("Catalog roots do not have unique source identities.")

    group_targets = defaultdict(list)
    target_roots = defaultdict(set)
    ids_by_root = defaultdict(Counter)
    controls = []
    for node in nodes:
        path = node["ELEMENT_PATH"]
        if path != "catalog" and not path.startswith("catalog."):
            continue
        root = node["SOURCE_RECORD_ID"]
        if root not in roots:
            raise ValueError("A Catalog node has no document root.")
        payload = json.loads(node["METADATA_JSON"])
        stack = [payload]
        while stack:
            item = stack.pop()
            identifier = item.get("id")
            if isinstance(identifier, str):
                ids_by_root[root][identifier] += 1
            stack.extend(item.get("parts", ()))
        if path in control_paths:
            controls.append((node, payload))
        if path in target_paths:
            kind, id_property = target_paths[path]
            content_ids = [prop.get("value") for prop in payload.get("props", ())
                           if prop.get("name") == id_property]
            if len(content_ids) != 1:
                raise ValueError("A Catalog target group lacks a unique source identity.")
            identity = (kind, _source_id(content_ids[0]))
            group_targets[(root, *identity)].append(payload.get("id"))
            target_roots[identity].add(root)

    outcomes = ("references", "added", "already_present", "unresolved_source", "outside_catalog",
                "group_not_in_candidate", "ambiguous_or_invalid_group_id")
    report = {kind: dict.fromkeys(outcomes, 0) for kind, _ in target_paths.values()}
    for node, payload in controls:
        references = [prop["value"] for prop in payload.get("props", ())
                      if prop.get("name") == "authoritative-subsection-reference"
                      and prop.get("ns") == "urn:archer:source:v1"]
        if not references:
            continue
        if len(references) != 1:
            raise ValueError("A Catalog control has multiple Subsection reference properties.")

        targets = {}
        for subsection in json.loads(references[0]):
            section = subsection.get("Section")
            for kind, member in (("subsection", subsection), ("section", section)):
                if member is None:
                    continue
                identity = (kind, _source_id(member["ContentId"]))
                # The hierarchy property omits Name for targets without a resolved title.
                targets[identity] = bool(member.get("Name")) or targets.get(identity, False)

        root = node["SOURCE_RECORD_ID"]
        links = payload.get("links", [])
        existing = {(link.get("rel"), link.get("href")) for link in links}
        additions = []
        for (kind, content_id), resolved in sorted(targets.items()):
            counts = report[kind]
            counts["references"] += 1
            candidates = group_targets.get((root, kind, content_id), ())
            if not resolved:
                counts["unresolved_source"] += 1
            elif not candidates:
                outcome = "outside_catalog" if (kind, content_id) in target_roots else "group_not_in_candidate"
                counts[outcome] += 1
            elif (len(candidates) != 1 or not _is_oscal_token(candidates[0])
                  or ids_by_root[root][candidates[0]] != 1):
                counts["ambiguous_or_invalid_group_id"] += 1
            else:
                href = "#" + quote(candidates[0], safe="-._~")
                if ("related", href) in existing:
                    counts["already_present"] += 1
                    continue
                additions.append({"rel": "related", "href": href})
                existing.add(("related", href))
                counts["added"] += 1
        if additions:
            payload["links"] = [*links, *additions]
            node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return report


def install_catalog_control_group_link_preview():
    contexts = globals().get("MAPPING_CONTEXTS") or []
    report = globals().get("PIPELINE_REPORT") or {}
    if (len(contexts) != 1 or globals().get("OSCAL_LOAD_MODE") != "PREVIEW"
            or report.get("status") != "PREVIEW_COMPLETE" or report.get("writes_executed") is not False):
        raise ValueError("Use the notebook session with the completed Catalog hierarchy Preview.")
    context = contexts[0]
    route, config, plan = context["route"], context["config"], context["compiled_plan"]
    native = plan.get("native_catalog") or {}
    groups = report.get("groups", [])
    if (config.get("OSCAL_MODEL") != "CATALOG" or config.get("WRITE_ALLOWED") is not False
            or config.get("EXECUTE_WRITES") is not False or route.get("write_allowed") is not False
            or not native or len(groups) != 1 or groups[0].get("source") != context["source_key"]
            or not groups[0].get("native_catalog", {}).get("NATIVE_CATALOG_CONTROL_HIERARCHY")):
        raise ValueError("Use the write-disabled Catalog route with the verified hierarchy enabled.")

    base_apply = _native_catalog_apply
    installed_fingerprint = getattr(base_apply, "catalog_control_group_links_fingerprint", None)
    if installed_fingerprint == plan["mapping_fingerprint"]:
        return base_apply
    if installed_fingerprint is not None:
        raise ValueError("Catalog link Preview mapping changed. Run the hierarchy Preview again.")
    if groups[0].get("mapping_fingerprint") != plan["mapping_fingerprint"]:
        raise ValueError("The completed hierarchy Preview is from a different mapping session.")
    owners = native.get("owner_bindings", native.get("declared_owner_bindings", {}))
    joined = route["joined_lookups"]
    subsection_path = max(owners, key=lambda path: path.count("."))
    subsection_lookup = owners[subsection_path]
    section_path = subsection_path.rsplit(".", 1)[0]
    section_lookup = owners.get(section_path)
    if not subsection_lookup or not section_lookup or joined[subsection_lookup].get("parent_binding") != section_lookup:
        raise ValueError("Catalog Section and Subsection bindings do not match the configured hierarchy.")
    target_paths = {
        section_path: ("section", joined[section_lookup]["child_record_id_property"]),
        subsection_path: ("subsection", joined[subsection_lookup]["child_record_id_property"]),
    }
    control_paths = set(native["paths"])
    base_fingerprint = plan["mapping_fingerprint"]
    fingerprint = hashlib.sha256((base_fingerprint + "\ncatalog-control-group-links-v1").encode()).hexdigest()

    def apply_group_links(nodes, edges, source_df, active):
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
        if not active["graph_report"].get("NATIVE_CATALOG_CONTROL_HIERARCHY"):
            raise ValueError("The Catalog hierarchy must run before the link mapping.")
        active["graph_report"]["NATIVE_CATALOG_CONTROL_GROUP_LINKS"] = _add_catalog_control_group_links(
            new_nodes, control_paths, target_paths)
        result_fingerprint = fingerprint
        if base_result_fingerprint != base_fingerprint:
            result_fingerprint = hashlib.sha256(json.dumps(
                [base_result_fingerprint, fingerprint], separators=(",", ":"),
            ).encode()).hexdigest()
        active_plan["mapping_fingerprint"] = result_fingerprint
        return new_nodes, new_edges

    apply_group_links.catalog_control_group_links_fingerprint = fingerprint
    plan["mapping_fingerprint"] = fingerprint
    return apply_group_links


_native_catalog_apply = install_catalog_control_group_link_preview()
print("Catalog Control links ready. Run Cell 7 in PREVIEW.")
