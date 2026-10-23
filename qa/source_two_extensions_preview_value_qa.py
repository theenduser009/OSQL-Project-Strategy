# Source Two approved extensions: run AFTER the successful current Cell 7 PREVIEW.
# Paste into a separate Python QA cell (Cell 8) after successful Cell 7 PREVIEW.
# Leave the seven mapper cells unchanged; run only this QA cell.
# Reads retained candidate/cached inputs only. No pipeline rerun, RAW/target
# queries, loader calls, temporary warehouse tables or target writes.
# Output is counts plus at most five existing IDs for missing statements.
import json
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from uuid import UUID

def qa_rows(frame):
    for row in frame.to_local_iterator():
        yield row.as_dict(recursive=True) if hasattr(row, "as_dict") else dict(row)

def qa_obj(value):
    if isinstance(value, str):
        value = json.loads(value, parse_float=Decimal)
    if not isinstance(value, dict):
        raise ValueError("QA_EXPECTED_JSON_OBJECT")
    return value

def qa_empty(value):
    return value is None or value == "" or value == [] or value == {}

def qa_scalar(value):
    if value is None or isinstance(value, (dict, list)):
        raise ValueError("QA_EXPECTED_SCALAR")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("QA_NONFINITE_SCALAR")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("QA_NONFINITE_SCALAR")
    text = ("true" if value else "false") if isinstance(value, bool) else str(value).strip()
    if not text or text.lower() in {"nan", "inf", "+inf", "-inf"}:
        raise ValueError("QA_NONFINITE_OR_BLANK_SCALAR")
    return text

def qa_refs(value):
    # Independent extraction of the accepted generic Source AR reference shape.
    if isinstance(value, dict):
        for key in ("UserList", "ValuesListIds", "ValueListIds",
                    "ContentId", "ContentIds", "Ids", "Value"):
            if key in value and not qa_empty(value[key]):
                return qa_refs(value[key])
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in {"valuelistid", "valuelistids", "valueslistid", "valueslistids"} and not qa_empty(item):
                return qa_refs(item)
        raise ValueError("QA_REFERENCE_SHAPE_REQUIRES_REVIEW")
    if isinstance(value, list):
        return [item for child in value for item in qa_refs(child)]
    return [qa_scalar(value)]

def qa_expected(raw, transform, aggregate):
    if qa_empty(raw):
        return Counter()
    if transform == "archer-select" and isinstance(raw, dict):
        ids = next((raw[key] for key in ("ValuesListIds", "ValueListIds")
                    if key in raw and not qa_empty(raw[key])), None)
        ids = ids if isinstance(ids, list) else [ids] if ids is not None else None
        values = raw.get("ResolvedValues")
        if ids is None or not isinstance(values, list) or len(ids) != len(values):
            raise ValueError("QA_SELECT_RESOLUTION_REQUIRES_REVIEW")
        labels = []
        for source_id, item in zip(ids, values):
            if (not isinstance(item, dict) or item.get("LookupStatus") != "MATCHED"
                    or str(item.get("ValueId", "")).strip() != str(source_id).strip()
                    or not isinstance(item.get("ValueName"), str) or not item["ValueName"].strip()):
                raise ValueError("QA_SELECT_RESOLUTION_REQUIRES_REVIEW")
            labels.append(item["ValueName"].strip())
        raw = labels
    if transform == "reference-ids":
        values = qa_refs(raw)
    else:
        values = [qa_scalar(item) for item in (raw if isinstance(raw, list) else [raw])]
    if aggregate and len(values) != 1:
        raise ValueError("QA_AGGREGATE_REQUIRES_ONE_VALUE")
    return Counter({value: 1 for value in values})

def qa_payload(node):
    return qa_obj(node["METADATA_JSON"])

def qa_source(record, context):
    if record["CURATED_JSON"] is None and context["compiled_plan"].get("options", {}).get("null_source_as_empty"):
        return {}
    return qa_obj(record["CURATED_JSON"])

def qa_check(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def qa_extension_text(value):
    """Independent accepted property text contract: no object stringification."""
    if qa_empty(value):
        return Counter()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("QA_EXTENSION_TEXT_REQUIRES_NONBLANK_STRING")
    return Counter({value.strip(): 1})

def qa_extension_metrics():
    return Counter({key: 0 for key in (
        "source_records", "populated_source_records", "expected_values",
        "actual_values", "missing_values", "unexpected_values", "exact_records",
        "normalization_review", "ownership_errors", "invalid_property_shape",
        "orphan_property_values")})

def qa_extension_compare(metric, raw, observed):
    metric["source_records"] += 1
    metric["actual_values"] += sum(observed.values())
    try:
        expected = qa_extension_text(raw)
    except (ValueError, TypeError, ArithmeticError):
        metric["normalization_review"] += 1
        return
    metric["populated_source_records"] += bool(expected)
    metric["expected_values"] += sum(expected.values())
    metric["missing_values"] += sum((expected - observed).values())
    metric["unexpected_values"] += sum((observed - expected).values())
    metric["exact_records"] += expected == observed

def qa_catalog_extensions(graph, source_input, load):
    """Match original frozen Source/child records without rebuilding the mapper."""
    ctx = graph["context"]
    expected_contract = {
        "INFORMATION": ("text", "information", "catalog.metadata.props[]"),
        "DPF_REFERENCE": ("text", "dpf-reference",
                          "catalog.groups[].groups[].groups[].props")}
    selected_contract = {
        row["SOURCE_FIELD_NAME"]: (
            row["TRANSFORM_ID"], row["REPRESENTATION_PARAMS"]["property_name"],
            row["OSCAL_ELEMENT_PATH"])
        for row in ctx["mapping_rows"]
        if row["SOURCE_FIELD_NAME"] in expected_contract}
    qa_check(selected_contract == expected_contract
             and sum(row["SOURCE_FIELD_NAME"] in expected_contract
                     for row in ctx["mapping_rows"]) == 2,
             "QA_CATALOG_EXTENSION_CONTRACT_MISMATCH")
    metrics = {"INFORMATION": qa_extension_metrics(),
               "DPF_REFERENCE": qa_extension_metrics()}
    info, dpf = metrics["INFORMATION"], metrics["DPF_REFERENCE"]
    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = defaultdict(list)
    for edge in qa_rows(graph["edges"]):
        if edge["DEPENDENCY_TYPE"] == "CONTAINS":
            parents[edge["FK_TARGET_ELEMENT_HASH"]].append(
                edge["FK_SOURCE_ELEMENT_HASH"])
    table = ctx["config"]["SOURCE_TABLE_NAME"]

    def one_parent(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None

    def same_owner(node, root):
        return (str(node["SOURCE_RECORD_ID"]) == root
                and node["SOURCE_TABLE_NAME"] == table)

    def identity(value):
        qa_check(value is not None and str(value).strip(),
                 "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    sources = {}
    for record in qa_rows(source_input["source_df"]):
        source_id = identity(record["SOURCE_RECORD_ID"])
        qa_check(source_id not in sources, "QA_DUPLICATE_FROZEN_SOURCE")
        sources[source_id] = qa_source(record, ctx)
    qa_check(len(sources) == source_input["selection"]["SELECTED_ROWS"]
             == load["source_records"], "QA_FROZEN_SOURCE_COUNT_MISMATCH")

    metadata = defaultdict(list)
    observed_info = defaultdict(Counter)
    for node in nodes.values():
        path = node["ELEMENT_PATH"]
        root = str(node["SOURCE_RECORD_ID"])
        if path == "catalog.metadata":
            metadata[root].append(node)
        if path != "catalog.metadata.props[]":
            continue
        prop = qa_payload(node)
        if prop.get("name") != "information":
            continue
        parent = one_parent(node)
        info["ownership_errors"] += int(not (
            parent is not None and parent["ELEMENT_PATH"] == "catalog.metadata"
            and same_owner(node, root) and same_owner(parent, root)))
        if set(prop) != {"name", "value"} or not isinstance(prop.get("value"), str):
            info["invalid_property_shape"] += 1
        if isinstance(prop.get("value"), str):
            observed_info[root][prop["value"]] += 1
    for root, obj in sources.items():
        owners = metadata.pop(root, [])
        info["ownership_errors"] += int(len(owners) != 1)
        for owner in owners:
            parent = one_parent(owner)
            info["ownership_errors"] += int(not (
                parent is not None and parent["ELEMENT_PATH"] == "catalog"
                and same_owner(owner, root) and same_owner(parent, root)))
        qa_extension_compare(info, obj.get("INFORMATION"),
                             observed_info.pop(root, Counter()))
    info["ownership_errors"] += sum(len(value) for value in metadata.values())
    info["orphan_property_values"] += sum(
        sum(value.values()) for value in observed_info.values())

    # Frame CONTENT_ID is the original parent record ID; _SOURCE_RECORD_ID is
    # the child's original record ID. Resolve all three levels independently.
    joined = ctx.get("lookups", {}).get("joined_sources", {})
    contracts = ctx.get("lookups", {}).get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    owner_records = {}
    previous = None
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict),
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        qa_check(contracts[binding].get("child_record_id_property")
                 == "archer-content-id", "QA_OWNER_PROVENANCE_CONTRACT_MISMATCH")
        records = {}
        for record in qa_rows(joined[binding]):
            child = identity(record["_SOURCE_RECORD_ID"])
            parent_id = identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in sources, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, ancestry = parent_id, ()
            else:
                qa_check(parent_id in owner_records[previous],
                         "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_records[previous][parent_id]
                root, ancestry = prior["root"], (parent_id,) + prior["ancestry"]
            records[child] = {"root": root, "ancestry": ancestry,
                              "object": qa_source(record, ctx)}
        owner_records[binding] = records
        previous = binding

    group_paths = {
        "catalog.groups[]": "topics",
        "catalog.groups[].groups[]": "sections",
        "catalog.groups[].groups[].groups[]": "subsections"}
    group_index = defaultdict(list)

    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [p.get("value") for p in props
                  if isinstance(p, dict) and p.get("name") == "archer-content-id"]
        if len(values) != 1 or not isinstance(values[0], str) or not values[0]:
            return None
        return values[0]

    for node in nodes.values():
        binding = group_paths.get(node["ELEMENT_PATH"])
        if binding is None:
            continue
        child = provenance(node)
        root = str(node["SOURCE_RECORD_ID"])
        if child is None:
            dpf["ownership_errors"] += 1
            continue
        original = owner_records[binding].get(child)
        if (original is None or original["root"] != root
                or not same_owner(node, root)):
            dpf["ownership_errors"] += 1
        group_index[(binding, root, child)].append(node)

    consumed = set()
    for child, original in owner_records["subsections"].items():
        root = original["root"]
        key = ("subsections", root, child)
        matches = group_index.get(key, [])
        consumed.add(key)
        dpf["ownership_errors"] += int(len(matches) != 1)
        observed = Counter()
        for owner in matches:
            # Prove the complete Section -> Topic -> Catalog parent chain.
            current = owner
            expected_chain = (
                ("catalog.groups[].groups[]", original["ancestry"][0]),
                ("catalog.groups[]", original["ancestry"][1]),
                ("catalog", None))
            for expected_path, expected_id in expected_chain:
                parent = one_parent(current)
                valid = (parent is not None and parent["ELEMENT_PATH"] == expected_path
                         and same_owner(parent, root))
                if valid and expected_id is not None:
                    valid = provenance(parent) == expected_id
                dpf["ownership_errors"] += int(not valid)
                if parent is None:
                    break
                current = parent
            props = qa_payload(owner).get("props", [])
            for prop in props:
                if not isinstance(prop, dict) or prop.get("name") != "dpf-reference":
                    continue
                if set(prop) != {"name", "value"} or not isinstance(prop.get("value"), str):
                    dpf["invalid_property_shape"] += 1
                if isinstance(prop.get("value"), str):
                    observed[prop["value"]] += 1
        qa_extension_compare(dpf, original["object"].get("DPF_REFERENCE"), observed)
    for key, extra_nodes in group_index.items():
        if key[0] != "subsections" or key in consumed:
            continue
        dpf["ownership_errors"] += len(extra_nodes)
        for owner in extra_nodes:
            dpf["orphan_property_values"] += sum(
                isinstance(prop, dict) and prop.get("name") == "dpf-reference"
                for prop in qa_payload(owner).get("props", []))
    return {field: dict(metric) for field, metric in metrics.items()}

def run_source_two_extensions_value_qa(model_graphs, source_inputs, pipeline_report, detail_limit=5):
    MODEL_GRAPHS, SOURCE_INPUTS, PIPELINE_REPORT = model_graphs, source_inputs, pipeline_report
    qa_check(type(detail_limit) is int and 0 <= detail_limit <= 5, "QA_DETAIL_LIMIT_ZERO_TO_FIVE")
    routes = {("source-two-source", "CATALOG"): 93,
              ("source-two-topic", "ASSESSMENT_RESULTS"): 7,
              ("source-two-section", "ASSESSMENT_RESULTS"): 10,
              ("source-two-subsection", "ASSESSMENT_RESULTS"): 16}
    qa_check(isinstance(MODEL_GRAPHS, dict) and set(MODEL_GRAPHS) == set(routes),
             "QA_EXPECTED_FOUR_SPRINT_ROUTES")
    qa_check(isinstance(SOURCE_INPUTS, dict)
             and {route[0] for route in routes}.issubset(SOURCE_INPUTS),
             "QA_EXPECTED_FOUR_FROZEN_INPUTS")
    for source_key in {route[0] for route in routes}:
        frozen = SOURCE_INPUTS[source_key]
        qa_check(isinstance(frozen, dict)
                 and callable(getattr(frozen.get("source_df"), "to_local_iterator", None))
                 and isinstance(frozen.get("selection"), dict)
                 and type(frozen["selection"].get("SELECTED_ROWS")) is int
                 and frozen["selection"]["SELECTED_ROWS"] >= 0,
                 "QA_FROZEN_SOURCE_FRAME_REQUIRED")
    qa_check(isinstance(PIPELINE_REPORT, dict), "QA_PREVIEW_REPORT_REQUIRED")
    qa_check(PIPELINE_REPORT.get("mode") == "PREVIEW"
             and PIPELINE_REPORT.get("status") == "PREVIEW_COMPLETE"
             and PIPELINE_REPORT.get("writes_executed") is False
             and PIPELINE_REPORT.get("commit_attempted") is False,
             "QA_SUCCESSFUL_NO_WRITE_PREVIEW_REQUIRED")
    groups = {(g.get("source"), g.get("model")): g for g in PIPELINE_REPORT.get("groups", [])}
    qa_check(set(groups) == set(routes) and len(PIPELINE_REPORT["groups"]) == 4,
             "QA_EXPECTED_FOUR_PREVIEW_RESULTS")
    for route, count in routes.items():
        ctx, load = MODEL_GRAPHS[route]["context"], groups[route]["load"]
        fingerprint = ctx["compiled_plan"].get("mapping_fingerprint")
        qa_check(isinstance(fingerprint, str) and bool(fingerprint.strip())
                 and ctx["routing_report"].get("STATUS") == "READY"
                 and ctx["routing_report"].get("SELECTED_ROWS") == count
                 and len(ctx["mapping_rows"]) == count
                 and ctx["config"].get("EXECUTE_WRITES") is False
                 and groups[route].get("mapping_fingerprint") == fingerprint,
                 "QA_RELEASE_SELECTION_MISMATCH")
        qa_check(load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
                 and load.get("target_dml_attempted") is False
                 and load.get("writes_executed") is False,
                 "QA_SUCCESSFUL_NO_WRITE_ROUTE_REQUIRED")
    
    result_path = "assessment-results.results[]"
    aggregate_path = result_path + ".props[]"
    finding_path = result_path + ".findings[]"
    finding_props = finding_path + ".props[]"
    aggregates = {"COMPLIANCE_RATING": ("archer-select", "compliance-rating", aggregate_path),
                  "COUNT_OF_NONCOMPLIANT_CONTROLS": ("direct", "noncompliant-count", aggregate_path),
                  "PCT_OF_NONCOMPLIANT_CONTROLS": ("direct", "noncompliant-percentage", aggregate_path)}
    finding_fields = {"FINDINGS": ("reference-ids", "source-finding-reference", finding_props),
                      "CONTROL_TESTING_RESULTS_FAILED_EXTERNAL_CONTROL_REQUIREMENT":
                          ("direct", "test-result", finding_props),
                      "DEVIATIONS_AUTHORITATIVE_SOURCES": ("direct", "deviation", finding_props),
                      "EVIDENCE_REPOSITORY": ("direct", "evidence-repository", finding_props)}
    child_summaries = []
    for route in routes:
        if route[1] != "ASSESSMENT_RESULTS":
            continue
        graph = MODEL_GRAPHS[route]
        ctx = graph["context"]
        expected_fields = dict(aggregates, **finding_fields)
        if route[0] == "source-two-subsection":
            expected_fields.update({
                "DEVIATIONS_AUTHORITATIVE_SOURCES_LINKED_TO_CONTROL_STANDARDS":
                    ("reference-ids", "linked-control-standard", finding_props),
                "DCMA_SCORE_VALUE": ("direct", "dcma-score-value", aggregate_path),
                "DCMA_SCORE_COMMENT": ("direct", "dcma-score-comment", aggregate_path)})
        if route[0] == "source-two-section":
            expected_fields.update({
                "AS_DEVIATION_CREATE_FLAG_CREATE":
                    ("archer-select", "as-deviation-create-flag-create", finding_props),
                "CREATE_DEVIATION_BINARY_AS":
                    ("direct", "create-deviation-binary-as", finding_props),
                "EVIDENCE_REPOSITORY_AUTHORITATIVE_SOURCE_SECTION_INPUT":
                    ("direct", "evidence-repository-authoritative-source-section-input", finding_props)})
        if route[0] == "source-two-subsection":
            expected_fields.update({
                "EVIDENCE_REPOSITORY_NIST_SUB_SECTIONS":
                    ("direct", "evidence-repository-nist-sub-sections", finding_props),
                "EVIDENCE_REPOSITORY_AUTHORITATIVE_SOURCE_SUBSECTION_INPUT":
                    ("direct", "evidence-repository-authoritative-source-subsection-input", finding_props),
                "EVIDENCE_REPOSITORY_RELATED_AUTHORITATIVE_SOURCES":
                    ("direct", "evidence-repository-related-authoritative-sources", finding_props),
                "EVIDENCE_REPOSITORY_NEW_SUB_SECTION_SELECTOR":
                    ("direct", "evidence-repository-new-sub-section-selector", finding_props),
                "EVIDENCE_REPOSITORY_SELECTED_AUTHORITATIVE_SOURCE_SUB_SECTIONS":
                    ("direct", "evidence-repository-selected-authoritative-source-sub-sections", finding_props),
                "EVIDENCE_REPOSITORY_RELATED_AUTHORITATIVE_SOURCE_SUB_SECTIONS":
                    ("direct", "evidence-repository-related-authoritative-source-sub-sections", finding_props)})
        actual_contract = {row["SOURCE_FIELD_NAME"]:
            (row["TRANSFORM_ID"], row["REPRESENTATION_PARAMS"]["property_name"], row["OWNER_ELEMENT_PATH"])
            for row in ctx["mapping_rows"]}
        qa_check(actual_contract == expected_fields, "QA_CHILD_FIELD_CONTRACT_MISMATCH")
        node_rows = list(qa_rows(graph["nodes"]))
        nodes = {n["NODE_KEY"]: n for n in node_rows}
        qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
        parents = defaultdict(list)
        for edge in qa_rows(graph["edges"]):
            if edge["DEPENDENCY_TYPE"] == "CONTAINS":
                parents[edge["FK_TARGET_ELEMENT_HASH"]].append(edge["FK_SOURCE_ELEMENT_HASH"])
        indexed = defaultdict(Counter)
        findings_by_source = Counter()
        results_by_source = Counter(n["SOURCE_RECORD_ID"] for n in nodes.values()
                                    if n["ELEMENT_PATH"] == result_path)
        allowed = {(path, name) for _, name, path in expected_fields.values()}
        unexpected = ownership_errors = 0
        for node in nodes.values():
            path = node["ELEMENT_PATH"]
            if path not in {aggregate_path, finding_path, finding_props}:
                continue
            parent_ids = parents[node["NODE_KEY"]]
            parent = nodes.get(parent_ids[0]) if len(parent_ids) == 1 else None
            parent_path = finding_path if path == finding_props else result_path
            good_owner = (parent is not None and parent["ELEMENT_PATH"] == parent_path
                          and parent["SOURCE_RECORD_ID"] == node["SOURCE_RECORD_ID"]
                          and parent["SOURCE_TABLE_NAME"] == node["SOURCE_TABLE_NAME"]
                          == ctx["config"]["SOURCE_TABLE_NAME"])
            ownership_errors += int(not good_owner)
            if path == finding_path:
                findings_by_source[node["SOURCE_RECORD_ID"]] += 1
                continue
            prop = qa_payload(node)
            name = prop.get("name")
            if ((path, name) not in allowed or not isinstance(prop.get("value"), str)
                    or set(prop) != {"name", "value"}):
                unexpected += 1
                continue
            indexed[(node["SOURCE_RECORD_ID"], path, name)][prop["value"]] += 1
        stats = {field: Counter() for field in expected_fields}
        source_ids = set()
        for record in qa_rows(SOURCE_INPUTS[route[0]]["source_df"]):
            source_id = record["SOURCE_RECORD_ID"]
            qa_check(source_id not in source_ids, "QA_DUPLICATE_FROZEN_SOURCE")
            source_ids.add(source_id)
            ownership_errors += int(results_by_source.pop(source_id, 0) != 1)
            obj = qa_source(record, ctx)
            expected_finding = False
            for field, (transform, name, path) in expected_fields.items():
                metric = stats[field]
                metric["source_records"] += 1
                observed = indexed.pop((source_id, path, name), Counter())
                try:
                    expected = qa_expected(obj.get(field), transform, path == aggregate_path)
                except (ValueError, TypeError, ArithmeticError):
                    metric["normalization_review"] += 1
                    continue
                expected_finding |= path == finding_props and bool(expected)
                metric["populated_source_records"] += bool(expected)
                metric["expected_values"] += sum(expected.values())
                metric["actual_values"] += sum(observed.values())
                metric["missing_values"] += sum((expected - observed).values())
                metric["unexpected_values"] += sum((observed - expected).values())
                metric["exact_records"] += expected == observed
            ownership_errors += int(findings_by_source.pop(source_id, 0) != int(expected_finding))
        qa_check(len(source_ids) == SOURCE_INPUTS[route[0]]["selection"]["SELECTED_ROWS"]
                 == groups[route]["load"]["source_records"], "QA_FROZEN_SOURCE_COUNT_MISMATCH")
        orphan_values = sum(sum(counter.values()) for counter in indexed.values())
        ownership_errors += sum(findings_by_source.values()) + sum(results_by_source.values())
        child_summaries.append({"route": route[0], "fields": dict(stats),
                                "unexpected_property_nodes": unexpected,
                                "orphan_property_values": orphan_values,
                                "ownership_errors": ownership_errors})
    
    route = ("source-two-source", "CATALOG")
    graph = MODEL_GRAPHS[route]
    ctx = graph["context"]
    catalog_extensions = qa_catalog_extensions(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    spec = ctx["compiled_plan"]["native_catalog"]
    qa_check(ctx["graph_report"].get("NATIVE_CATALOG_FIELD_VALUE_CHECK")
             == "CANDIDATE_MATCHES_FROZEN_TARGET_FIELDS", "QA_NATIVE_FROZEN_FIELD_CHECK_REQUIRED")
    contract = spec["guid_props"]
    lookup = spec["lookup"]
    qa_check(contract["source_field"] == "RELATED_CONTROL_PROCEDURES"
             and contract["namespace_mode"] == "archer-field-guid-urn"
             and contract["property_name"] == "procedure-reference",
             "QA_PROCEDURE_CONTRACT_MISMATCH")
    metadata = list(qa_rows(ctx["lookups"]["native_control_guid_metadata"][lookup]))
    matched = [r for r in metadata if r["LEVEL_ID"] == 41 and r["FIELD_ID"] == 30705
               and r["SQL_FIELD_NAME"] == "RELATED_CONTROL_PROCEDURES"]
    qa_check(len(matched) == 1, "QA_EXACT_GUID_METADATA_BINDING_REQUIRED")
    field_guid = UUID(matched[0]["FIELD_GUID"])
    qa_check(str(field_guid) == matched[0]["FIELD_GUID"].lower(),
             "QA_CANONICAL_GUID_REQUIRED")
    same_guid = 0
    for row in metadata:
        try:
            same_guid += UUID(row["FIELD_GUID"]) == field_guid
        except (ValueError, TypeError, AttributeError):
            pass
    qa_check(same_guid == 1, "QA_FIELD_GUID_NOT_UNIQUE")
    namespace = field_guid.urn
    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {n["NODE_KEY"]: n for n in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = defaultdict(list)
    for edge in qa_rows(graph["edges"]):
        if edge["DEPENDENCY_TYPE"] == "CONTAINS":
            parents[edge["FK_TARGET_ELEMENT_HASH"]].append(edge["FK_SOURCE_ELEMENT_HASH"])
    # Independent Catalog+Standard association closure, without rebuilding LCA
    # placement or controls. Owner-group provenance already exists in the graph.
    owner_bindings = spec["owner_bindings"]
    frames = {None: SOURCE_INPUTS[route[0]]["source_df"],
              **ctx["lookups"].get("joined_sources", {})}
    owner_documents = {}
    reference_field = spec["fields"][""]
    for binding in set(owner_bindings.values()):
        qa_check(binding in frames, "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records = {}
        for record in qa_rows(frames[binding]):
            source_id = str(record["SOURCE_RECORD_ID" if binding is None else "_SOURCE_RECORD_ID"])
            qa_check(source_id not in records, "QA_DUPLICATE_FROZEN_OWNER")
            records[source_id] = qa_source(record, ctx).get(reference_field)
        owner_documents[binding] = records
    associations = set()
    for owner in nodes.values():
        if owner["ELEMENT_PATH"] not in owner_bindings:
            continue
        binding = owner_bindings[owner["ELEMENT_PATH"]]
        if binding is None:
            source_id = owner["SOURCE_RECORD_ID"]
        else:
            provenance_name = ctx["lookups"]["joined_contract"][binding]["child_record_id_property"]
            values = [p.get("value") for p in qa_payload(owner).get("props", [])
                      if p.get("name") == provenance_name]
            qa_check(len(values) == 1, "QA_OWNER_PROVENANCE_REQUIRED")
            source_id = values[0]
        qa_check(source_id in owner_documents[binding], "QA_FROZEN_OWNER_DOCUMENT_MISSING")
        references = owner_documents[binding][source_id]
        if references is None:
            continue
        qa_check(isinstance(references, list), "QA_DIRECT_STANDARD_REFERENCES_MUST_BE_ARRAY")
        for standard_id in references:
            qa_check(type(standard_id) is int and standard_id > 0,
                     "QA_DIRECT_STANDARD_REFERENCE_REQUIRES_POSITIVE_INTEGER")
            associations.add((owner["SOURCE_RECORD_ID"], str(standard_id)))
    controls = [n for n in nodes.values() if n["ELEMENT_PATH"] in spec["paths"]]
    expected_associations = Counter({pair: 1 for pair in associations})
    actual_associations = Counter((n["SOURCE_RECORD_ID"], n["INSTANCE_KEY"]) for n in controls)
    association_summary = {"expected_catalog_standard_pairs": len(expected_associations),
                           "actual_control_occurrences": sum(actual_associations.values()),
                           "missing_associations": sum((expected_associations - actual_associations).values()),
                           "unexpected_associations": sum((actual_associations - expected_associations).values()),
                           "placement_scope": "Independent Catalog/Standard association and containment; LCA policy remains the completed mapper contract"}
    qa_check(bool(controls), "QA_NO_CONTROL_OCCURRENCES")
    needed = {n["INSTANCE_KEY"] for n in controls}
    standards = {}
    for record in qa_rows(ctx["lookups"]["native_control_sources"][lookup]):
        source_id = record["SOURCE_RECORD_ID"]
        if source_id in needed:
            qa_check(source_id not in standards, "QA_DUPLICATE_FROZEN_STANDARD")
            standards[source_id] = qa_source(record, ctx)
    qa_check(set(standards) == needed, "QA_FROZEN_STANDARD_COVERAGE")
    procedure_summary = {path: Counter() for path in spec["paths"]}
    statement_summary = Counter()
    statement_details = []
    missing_standard_ids = set()
    for node in controls:
        metric = procedure_summary[node["ELEMENT_PATH"]]
        metric["control_occurrences"] += 1
        payload = qa_payload(node)
        standard_id = node["INSTANCE_KEY"]
        original = standards[standard_id]
        ids = [p.get("value") for p in payload.get("props", [])
               if p.get("name") == "archer-content-id"]
        metric["identity_errors"] += int(ids != [standard_id])
        parent_ids = parents[node["NODE_KEY"]]
        parent = nodes.get(parent_ids[0]) if len(parent_ids) == 1 else None
        metric["ownership_errors"] += int(not (
            parent is not None and parent["ELEMENT_PATH"] == node["PARENT_NODE_PATH"]
            == node["ELEMENT_PATH"].rsplit(".", 1)[0]
            and parent["INSTANCE_KEY"] == node["PARENT_INSTANCE_KEY"]
            and parent["SOURCE_RECORD_ID"] == node["SOURCE_RECORD_ID"]
            and parent["SOURCE_TABLE_NAME"] == node["SOURCE_TABLE_NAME"]
            == ctx["config"]["SOURCE_TABLE_NAME"]))
        references = original.get("RELATED_CONTROL_PROCEDURES")
        if references is None:
            references = []
        qa_check(isinstance(references, list), "QA_PROCEDURE_REFERENCE_SHAPE")
        expected_ids = set()
        for ref in references:
            qa_check(isinstance(ref, dict) and type(ref.get("ContentId")) is int
                     and ref["ContentId"] > 0 and type(ref.get("LevelId")) is int
                     and ref["LevelId"] == 39, "QA_PROCEDURE_REFERENCE_SHAPE")
            expected_ids.add(str(ref["ContentId"]))
        expected = Counter({("procedure-reference", namespace, value): 1 for value in expected_ids})
        selected = [p for p in payload.get("props", [])
                    if (p.get("name"), p.get("ns")) == ("procedure-reference", namespace)]
        metric["preserved_same_name_other_namespace"] += sum(
            p.get("name") == "procedure-reference" and p.get("ns") != namespace
            for p in payload.get("props", []))
        actual = Counter()
        for prop in selected:
            if set(prop) != {"name", "ns", "value"} or not all(isinstance(prop.get(k), str)
                                                            for k in ("name", "ns", "value")):
                metric["invalid_property_shape"] += 1
            else:
                actual[(prop["name"], prop["ns"], prop["value"])] += 1
        metric["expected_values"] += sum(expected.values())
        metric["actual_values"] += sum(actual.values())
        metric["missing_values"] += sum((expected - actual).values())
        metric["unexpected_values"] += sum((actual - expected).values())
        metric["exact_control_occurrences"] += actual == expected
        statement_field = spec["fields"]["parts"]
        source_statement = original.get(statement_field)
        source_absence = ("SOURCE_KEY_ABSENT" if statement_field not in original else
                          "SOURCE_NULL" if source_statement is None else
                          "SOURCE_BLANK" if isinstance(source_statement, str) and not source_statement.strip()
                          else "SOURCE_POPULATED")
        statements = [p for p in payload.get("parts", []) if p.get("name") == "statement"]
        if not statements:
            statement_summary["missing_statement_occurrences"] += 1
            missing_standard_ids.add(standard_id)
            statement_summary[source_absence] += 1
            if len(statement_details) < detail_limit:
                statement_details.append({"catalog_source_id": node["SOURCE_RECORD_ID"],
                                          "standard_content_id": standard_id,
                                          "control_path": node["ELEMENT_PATH"],
                                          "reason": source_absence})
        if source_absence == "SOURCE_POPULATED":
            statement_summary["populated_source_missing_statement"] += int(not statements)
        else:
            statement_summary["empty_source_with_statement"] += bool(statements)
    statement_summary["distinct_standards_with_missing_statement"] = len(missing_standard_ids)
    errors = sum(row["unexpected_property_nodes"] + row["orphan_property_values"]
                 + row["ownership_errors"] for row in child_summaries)
    errors += sum(metric.get(key, 0) for row in child_summaries for metric in row["fields"].values()
                  for key in ("normalization_review", "missing_values", "unexpected_values"))
    errors += sum(metric.get(key, 0) for metric in procedure_summary.values()
                  for key in ("identity_errors", "ownership_errors", "invalid_property_shape",
                              "missing_values", "unexpected_values"))
    errors += association_summary["missing_associations"] + association_summary["unexpected_associations"]
    errors += statement_summary["populated_source_missing_statement"] + statement_summary["empty_source_with_statement"]
    errors += sum(metric.get(key, 0) for metric in catalog_extensions.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "orphan_property_values"))
    return {"catalog_extension_properties": catalog_extensions,
            "child_assessment_results": child_summaries,
            "procedure_by_control_path": procedure_summary,
            "catalog_standard_associations": association_summary,
            "missing_statement_classification": statement_summary,
            "statement_content_scope": "Full id/title/statement equality already passed the mapper frozen-field check; this QA classifies omission occurrences",
            "missing_statement_id_details_private": statement_details,
            "error_count": errors,
            "result": "PASS" if errors == 0 else "REVIEW_REQUIRED",
            "scope": "Frozen preview parity only; no persistence/full-document-conformance claim"}

qa_session_names = ("MODEL_GRAPHS", "SOURCE_INPUTS", "PIPELINE_REPORT")
qa_session_present = [name for name in qa_session_names if name in globals()]
if __name__ == "__main__" or qa_session_present:
    if len(qa_session_present) != len(qa_session_names):
        raise RuntimeError("QA_PREVIEW_SESSION_REQUIRED")
    SOURCE_TWO_EXTENSIONS_VALUE_QA = run_source_two_extensions_value_qa(
        MODEL_GRAPHS, SOURCE_INPUTS, PIPELINE_REPORT)
    print("SOURCE_TWO_EXTENSIONS_PREVIEW_VALUE_QA")
    print(json.dumps(SOURCE_TWO_EXTENSIONS_VALUE_QA, indent=2, default=str))
    if SOURCE_TWO_EXTENSIONS_VALUE_QA["error_count"]:
        raise RuntimeError("QA_VALUE_OR_OWNERSHIP_REVIEW_REQUIRED")
