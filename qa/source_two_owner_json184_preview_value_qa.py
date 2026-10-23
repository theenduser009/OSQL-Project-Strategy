# Source Two owner-json184 QA: all159 checks plus four permissions and21 explicit opaque-JSON fields.
# Paste into a separate Python QA cell (Cell 8) after successful Cell 7 PREVIEW.
# Leave the seven mapper cells unchanged; run only this QA cell.
# Streams retained preview frames using Snowpark retrieval actions.
# Does not rerun the pipeline, call loaders, approve commits, create warehouse
# tables or write targets. Release validation, not an extra daily ETL cell.
# Prints phase labels, then counts and at most five existing missing-statement IDs.
import json
import hashlib
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from uuid import UUID

# Audit-local reuse changes cost only; all rows, duplicates and comparisons remain.
from collections import OrderedDict
from contextvars import ContextVar
from functools import wraps
from itertools import chain
import sys

_QA_DECODE_MAX_ENTRIES = 128
_QA_DECODE_MAX_BYTES = 8 * 1024 * 1024
_QA_AUDIT_REUSE = ContextVar("source_two_owner_json184_audit_reuse", default=None)


def _qa_decoded_size(value, limit):
    """Account cached Python objects without building a large traversal worklist."""
    total, seen = 0, set()
    stack = [iter((value,))]
    while stack:
        try:
            item = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        identity = id(item)
        if identity in seen:
            continue
        seen.add(identity)
        total += sys.getsizeof(item)
        if total > limit:
            return None
        if isinstance(item, dict):
            stack.append(iter(chain.from_iterable(item.items())))
        elif isinstance(item, (list, tuple)):
            stack.append(iter(item))
    return total


class _QaParentLookup(dict):
    def __missing__(self, key):
        # Match the old empty-parent lookup without accumulating missing keys.
        return ()


def _qa_build_parent_index(frame):
    parents = defaultdict(list)
    for edge in qa_rows(frame):
        if edge["DEPENDENCY_TYPE"] == "CONTAINS":
            parents[edge["FK_TARGET_ELEMENT_HASH"]].append(edge["FK_SOURCE_ELEMENT_HASH"])
    return _QaParentLookup((key, tuple(values)) for key, values in parents.items())


class _QaAuditReuseScope:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self._decode_cache = OrderedDict()
        self._decode_bytes = 0
        self._parent_frame = None
        self._parent_index = None

    def decode(self, raw, parse_decimal):
        mode = bool(parse_decimal)
        if type(raw) is not str or sys.getsizeof(raw) > _QA_DECODE_MAX_BYTES:
            return json.loads(raw, parse_float=Decimal) if mode else json.loads(raw)
        key = (raw, mode)
        if key in self._decode_cache:
            value, size = self._decode_cache.pop(key)
            self._decode_cache[key] = (value, size)
            return value
        value = json.loads(raw, parse_float=Decimal) if mode else json.loads(raw)
        overhead = (sys.getsizeof(raw) + sys.getsizeof(key)
                    + sys.getsizeof((value, 0)) + 192)
        size = _qa_decoded_size(value, _QA_DECODE_MAX_BYTES - overhead)
        if size is None:
            return value  # Oversized data is still fully checked; only reuse is bypassed.
        size += overhead
        while self._decode_cache and (
                len(self._decode_cache) >= _QA_DECODE_MAX_ENTRIES
                or self._decode_bytes + size > _QA_DECODE_MAX_BYTES):
            _, (_, removed) = self._decode_cache.popitem(last=False)
            self._decode_bytes -= removed
        if size <= _QA_DECODE_MAX_BYTES:
            self._decode_cache[key] = (value, size)
            self._decode_bytes += size
        return value

    def parents(self, frame):
        if self._parent_frame is not frame:
            # Cache only one repeated Catalog edge frame; preserve original identity.
            self._parent_index = _qa_build_parent_index(frame)
            self._parent_frame = frame
        return self._parent_index

    def phase(self, name, state):
        if self.progress_callback is not None:
            self.progress_callback(name, state)

    def close(self):
        self._decode_cache.clear()
        self._decode_bytes = 0
        self._parent_index = None
        self._parent_frame = None
        self.progress_callback = None


def _qa_decode_json(raw, parse_decimal):
    scope = _QA_AUDIT_REUSE.get()
    if scope is None:
        return json.loads(raw, parse_float=Decimal) if parse_decimal else json.loads(raw)
    return scope.decode(raw, parse_decimal)


def qa_parent_index(graph):
    scope = _QA_AUDIT_REUSE.get()
    context = graph["context"]
    if (scope is not None and context.get("source_key") == "source-two-source"
            and context.get("config", {}).get("OSCAL_MODEL") == "CATALOG"):
        return scope.parents(graph["edges"])
    return _qa_build_parent_index(graph["edges"])


def _qa_compact_provenance(function):
    """One small result per validated unique node, local to one helper call."""
    cache = {}
    @wraps(function)
    def read(node):
        key = node["NODE_KEY"]
        if key not in cache:
            cache[key] = function(node)
        return cache[key]
    return read


def _qa_phase(name, state):
    scope = _QA_AUDIT_REUSE.get()
    if scope is not None:
        scope.phase(name, state)


def qa_rows(frame):
    for row in frame.to_local_iterator():
        yield row.as_dict(recursive=True) if hasattr(row, "as_dict") else dict(row)

def qa_obj(value):
    if isinstance(value, str):
        value = _qa_decode_json(value, True)
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
    # INFORMATION also exists on Topic parts. Identify the two new mappings by
    # original field AND registry owner; never shadow one owner with another.
    expected_contract = {
        ("INFORMATION", "catalog.metadata.props[]"):
            ("text", "information", "catalog.metadata.props[]", None),
        ("DPF_REFERENCE", "catalog.groups[].groups[].groups[]"):
            ("text", "dpf-reference",
             "catalog.groups[].groups[].groups[].props", "subsections")}
    selected_rows = [
        row for row in ctx["mapping_rows"]
        if (row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]) in expected_contract]
    selected_contract = {
        (row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]): (
            row["TRANSFORM_ID"], row["REPRESENTATION_PARAMS"]["property_name"],
            row["OSCAL_ELEMENT_PATH"],
            row["REPRESENTATION_PARAMS"].get("joined_lookup"))
        for row in selected_rows}
    qa_check(selected_contract == expected_contract and len(selected_rows) == 2,
             "QA_CATALOG_EXTENSION_CONTRACT_MISMATCH")
    metrics = {"INFORMATION": qa_extension_metrics(),
               "DPF_REFERENCE": qa_extension_metrics()}
    info, dpf = metrics["INFORMATION"], metrics["DPF_REFERENCE"]
    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
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

    @_qa_compact_provenance
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


def qa_owner_reference_values(raw):
    """Independently decode the reviewed owner field, never a URI or entity."""
    if raw is None or raw == []:
        return Counter()
    if not isinstance(raw, list):
        raise ValueError("QA_OWNER_REFERENCES_REQUIRE_LEVEL39_OBJECT_ARRAY")
    identifiers = set()
    for item in raw:
        if (not isinstance(item, dict) or type(item.get("ContentId")) is not int
                or item["ContentId"] <= 0 or type(item.get("LevelId")) is not int
                or item["LevelId"] != 39):
            raise ValueError("QA_OWNER_REFERENCES_REQUIRE_LEVEL39_OBJECT_ARRAY")
        identifiers.add(str(item["ContentId"]))
    return Counter({identifier: 1 for identifier in identifiers})

def qa_owner_procedure_properties(graph, source_input, load):
    """Check only the four exact owner GUID families on the retained preview."""
    ctx = graph["context"]
    owner_rows = [row for row in ctx["mapping_rows"]
                  if row.get("TRANSFORM_ID") == "catalog-owner-procedure-props"]
    spec = ctx["compiled_plan"].get("owner_procedure_props")
    if spec is None:
        qa_check(not owner_rows, "QA_OWNER_FEATURE_PLAN_REQUIRED")
        return {"status": "NOT_ENABLED", "owners": {},
                "scope": "Current126-rule release; no owner reference activation"}
    qa_check(isinstance(spec, dict)
             and spec.get("release") == "catalog-owner-procedure-props-review-v1",
             "QA_OWNER_FEATURE_RELEASE_MISMATCH")
    expected = {
        "catalog.metadata.props[]": (None, 6, 30706, "catalog.metadata.props[]"),
        "catalog.groups[]": ("topics", 7, 30708, "catalog.groups[].props"),
        "catalog.groups[].groups[]": ("sections", 8, 30710,
                                      "catalog.groups[].groups[].props"),
        "catalog.groups[].groups[].groups[]": ("subsections", 9, 30712,
                                               "catalog.groups[].groups[].groups[].props")}
    contracts = spec.get("contracts")
    qa_check(isinstance(contracts, dict) and set(contracts) == set(expected)
             and len(owner_rows) == 4
             and {row.get("OWNER_ELEMENT_PATH") for row in owner_rows} == set(expected),
             "QA_EXACT_FOUR_OWNER_CONTRACTS_REQUIRED")
    lookups = ctx.get("lookups", {})
    native = ctx["compiled_plan"].get("native_catalog") or {}
    standard = native.get("guid_props")
    qa_check(native.get("lookup") == "control-standards"
             and isinstance(standard, dict) and standard.get("enabled") is True
             and standard.get("source_field") == "RELATED_CONTROL_PROCEDURES"
             and standard.get("level_id") == 41 and standard.get("field_id") == 30705
             and lookups.get("native_control_guid_contract", {}).get("control-standards") == standard,
             "QA_EXISTING_STANDARD_GUID_DOMAIN_REQUIRED")
    standard_frame = lookups.get("native_control_guid_metadata", {}).get("control-standards")
    frames = lookups.get("owner_procedure_guid_metadata", {})
    qa_check(callable(getattr(standard_frame, "to_local_iterator", None))
             and isinstance(frames, dict)
             and set(frames) == set(expected)
             and all(frame is standard_frame for frame in frames.values())
             and lookups.get("owner_procedure_guid_contract") == contracts,
             "QA_ONE_COMPLETE_FROZEN_GUID_DOMAIN_REQUIRED")
    projection = ("metadata_table", "level_id_column", "field_id_column",
                  "guid_column", "source_field_column")
    allowed = {"enabled", "source_field", "level_id", "field_id", "namespace_mode",
               "property_name", "metadata_table", "level_id_column", "field_id_column",
               "guid_column", "source_field_column", "value_encoding", "owner_path", "joined_lookup"}
    for row in owner_rows:
        owner = row["OWNER_ELEMENT_PATH"]
        binding, level, field, target = expected[owner]
        contract, params = contracts[owner], row.get("REPRESENTATION_PARAMS", {})
        qa_check(isinstance(contract, dict) and set(contract) == allowed
                 and contract.get("enabled") is True and contract.get("owner_path") == owner
                 and contract.get("source_field") == "RELATED_CONTROL_PROCEDURES"
                 and type(contract.get("level_id")) is int and contract["level_id"] == level
                 and type(contract.get("field_id")) is int and contract["field_id"] == field
                 and contract.get("joined_lookup") == binding
                 and contract.get("namespace_mode") == "archer-field-guid-urn"
                 and contract.get("property_name") == "procedure-reference"
                 and contract.get("value_encoding") == "one-string-per-procedure-id"
                 and all(contract.get(key) == standard.get(key) for key in projection)
                 and row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("SOURCE_FIELD_NAME") == "RELATED_CONTROL_PROCEDURES"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if binding is None else "props")
                 and params.get("owner_procedure_binding") == owner
                 and params.get("joined_lookup") == binding
                 and params.get("property_name") == "procedure-reference",
                 "QA_OWNER_FIELD_AND_TARGET_CONTRACT_MISMATCH")

    metadata = list(qa_rows(standard_frame))
    qa_check(all({"LEVEL_ID", "FIELD_ID", "FIELD_GUID", "SQL_FIELD_NAME"}.issubset(row)
                 for row in metadata), "QA_FIELD_GUID_METADATA_COLUMNS_REQUIRED")
    def metadata_id(value):
        if type(value) is int:
            return value
        if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
            return int(value)
        return None
    def namespace_for(level, field):
        rows = [row for row in metadata if metadata_id(row["LEVEL_ID"]) == level
                and metadata_id(row["FIELD_ID"]) == field]
        qa_check(len(rows) == 1 and rows[0]["SQL_FIELD_NAME"] == "RELATED_CONTROL_PROCEDURES",
                 "QA_EXACT_OWNER_FIELD_GUID_ROW_REQUIRED")
        value = rows[0]["FIELD_GUID"]
        qa_check(isinstance(value, str) and value == value.strip(),
                 "QA_CANONICAL_OWNER_FIELD_GUID_REQUIRED")
        try:
            guid = UUID(value)
        except (ValueError, TypeError, AttributeError):
            raise RuntimeError("QA_CANONICAL_OWNER_FIELD_GUID_REQUIRED") from None
        qa_check(str(guid) == value.lower(), "QA_CANONICAL_OWNER_FIELD_GUID_REQUIRED")
        count = 0
        for row in metadata:
            try:
                count += UUID(row["FIELD_GUID"]) == guid
            except (ValueError, TypeError, AttributeError):
                pass
        qa_check(count == 1, "QA_OWNER_FIELD_GUID_NOT_UNIQUE")
        return guid.urn
    namespaces = {owner: namespace_for(level, field)
                  for owner, (_, level, field, _) in expected.items()}
    standard_namespace = namespace_for(41, 30705)
    qa_check(len(set(namespaces.values())) == 4
             and standard_namespace not in namespaces.values(),
             "QA_DISTINCT_OWNER_FIELD_GUID_NAMESPACES_REQUIRED")
    namespace_owners = {namespace: owner for owner, namespace in namespaces.items()}
    metrics = {owner: qa_extension_metrics() for owner in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()
    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        source_id = identity(record["SOURCE_RECORD_ID"])
        qa_check(source_id not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[source_id] = qa_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (source_id, source_id): {"object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for source_id, obj in source_docs.items()}}
    joined, joined_contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(joined_contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    previous, owner_index = None, {}
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in joined_contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(joined_contracts[binding], dict)
                 and joined_contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owner_docs = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            obj = qa_source(record, ctx)
            records[child] = {"root": root, "chain": chain}
            owner_docs[(root, child)] = {"object": obj, "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owner_docs
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    observed = {owner: defaultdict(Counter) for owner in expected}
    groups = defaultdict(list)
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            root, child = str(node["SOURCE_RECORD_ID"]), provenance(node)
            if child is None:
                metrics[owner]["ownership_errors"] += 1
            else:
                groups[(owner, root, child)].append(node)
        payload = qa_payload(node)
        located = []
        payload_ns = payload.get("ns")
        if (payload.get("name") == "procedure-reference" or
                isinstance(payload_ns, str) and payload_ns in namespace_owners):
            located.append((payload, True))
        props = payload.get("props", [])
        qa_check(isinstance(props, list), "QA_PROPERTIES_MUST_BE_ARRAY")
        located.extend((prop, False) for prop in props if isinstance(prop, dict)
                       and (prop.get("name") == "procedure-reference" or
                            isinstance(prop.get("ns"), str)
                            and prop["ns"] in namespace_owners))
        for prop, standalone in located:
            namespace = prop.get("ns")
            intended_owner = namespace_owners.get(namespace) if isinstance(namespace, str) else None
            if intended_owner is None:
                continue  # Standard-owned and unrelated namespace families are distinct.
            metric = metrics[intended_owner]
            valid_location = (owner == intended_owner and
                              standalone == (owner == "catalog.metadata.props[]"))
            if not valid_location:
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            if (set(prop) != {"name", "ns", "value"}
                    or prop.get("name") != "procedure-reference" or not all(
                        isinstance(prop.get(key), str) for key in ("name", "ns", "value"))):
                metric["invalid_property_shape"] += 1
            if isinstance(prop.get("value"), str):
                observed[intended_owner][(root, child)][prop["value"]] += 1
            if standalone:
                current = node
                for path, _ in documents[intended_owner].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for owner, owners in documents.items():
        metric = metrics[owner]
        for key, record in owners.items():
            root, child = key
            if owner != "catalog.metadata.props[]":
                matches = groups.pop((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    current = node
                    for path, expected_id in record["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[owner].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            try:
                desired = qa_owner_reference_values(record["object"].get("RELATED_CONTROL_PROCEDURES"))
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired)
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(sum(counter.values()) for counter in observed[owner].values())
    for (owner, _, _), extra in groups.items():
        metrics[owner]["ownership_errors"] += len(extra)
    return {"status": "CHECKED", "owners": {owner: dict(metric) for owner, metric in metrics.items()},
            "scope": "Independent original-owner Level39 references; no native links/entities or persistence claim"}


def qa_policy_scalar_properties(graph, source_input, load):
    """Independently compare the eight approved raw scalar owner properties."""
    expected = {
        "NUMBER_OF_POLICIES_SOURCE_LEVEL":
            ("catalog.metadata.props[]", None, "number-of-policies-source-level"),
        "NUMBER_OF_POLICIES_TOPIC_LEVEL":
            ("catalog.groups[]", "topics", "number-of-policies-topic-level"),
        "TOTAL_NUMBER_OF_SECTIONS_LINKED_TO_POLICY":
            ("catalog.groups[]", "topics", "total-number-of-sections-linked-to-policy"),
        "PERCENT_OF_SECTIONS_LINKED_TO_POLICY":
            ("catalog.groups[]", "topics", "percent-of-sections-linked-to-policy"),
        "NUMBER_OF_POLICIES_SECTION_LEVEL":
            ("catalog.groups[].groups[]", "sections", "number-of-policies-section-level"),
        "TOTAL_NUMBER_OF_SUB_SECTIONS_LINKED_TO_POLICY":
            ("catalog.groups[].groups[]", "sections", "total-number-of-sub-sections-linked-to-policy"),
        "PERCENT_OF_SUB_SECTIONS_LINKED_TO_POLICY":
            ("catalog.groups[].groups[]", "sections", "percent-of-sub-sections-linked-to-policy"),
        "NUMBER_OF_POLICIES_SUB_SECTION_LEVEL":
            ("catalog.groups[].groups[].groups[]", "subsections",
             "number-of-policies-sub-section-level")}
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if row.get("SOURCE_FIELD_NAME") in expected]
    if not rows:
        return {"status": "NOT_ENABLED", "fields": {},
                "scope": "No eight-policy scalar activation"}
    qa_check(len(rows) == 8 and {row["SOURCE_FIELD_NAME"] for row in rows} == set(expected),
             "QA_EXACT_EIGHT_POLICY_CONTRACTS_REQUIRED")
    for row in rows:
        field = row["SOURCE_FIELD_NAME"]
        owner, lookup, name = expected[field]
        params = row.get("REPRESENTATION_PARAMS", {})
        target = owner if lookup is None else owner + ".props"
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else "props")
                 and row.get("TRANSFORM_ID") == "direct"
                 and params.get("joined_lookup") == lookup
                 and params.get("property_name") == name,
                 "QA_POLICY_FIELD_AND_OWNER_CONTRACT_MISMATCH")
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = {name: field for field, (_, _, name) in expected.items()}
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    def policy_family(prop):
        # These reviewed properties are unqualified. A same-name property in a
        # separate nonempty namespace belongs to a different property family.
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and name in names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True)] if policy_family(payload) else []
        props = payload.get("props", [])
        qa_check(isinstance(props, list), "QA_PROPERTIES_MUST_BE_ARRAY")
        located.extend((prop, False) for prop in props
                       if isinstance(prop, dict) and policy_family(prop))
        for prop, standalone in located:
            field = names[prop["name"]]
            intended, lookup, _ = expected[field]
            metric = metrics[field]
            if owner != intended or standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            if set(prop) != {"name", "value"} or not isinstance(prop.get("value"), str):
                metric["invalid_property_shape"] += 1
            if isinstance(prop.get("value"), str):
                observed[field][(root, child)][prop["value"]] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (owner, lookup, _) in expected.items():
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field)
            try:
                # Direct scalar semantics only; never calculate or attach units.
                desired = qa_expected(raw, "direct", True)
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired)
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    return {"status": "CHECKED", "fields": {field: dict(metric) for field, metric in metrics.items()},
            "scope": "Original owner raw scalar parity only; no calculations/units/native policy entities"}

def qa_owner_flag_label_properties(graph, source_input, load):
    """Independently compare twelve original-owner flags/labels, never parent titles."""
    expected = {
        ("LINKED_TO_POLICY_SOURCE_LEVEL", "catalog.metadata.props[]"):
            (None, "linked-to-policy-source-level", "archer-select"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SOURCE", "catalog.metadata.props[]"):
            (None, "engagement-scope-in-control-source", "archer-select"),
        ("LINKED_TO_POLICY_TOPIC_LEVEL", "catalog.groups[]"):
            ("topics", "linked-to-policy-topic-level", "archer-select"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_TOPIC", "catalog.groups[]"):
            ("topics", "engagement-scope-in-control-topic", "archer-select"),
        ("SOURCE_NAME_CALC_FIELD", "catalog.groups[]"):
            ("topics", "source-name-calc-field", "text"),
        ("LINKED_TO_POLICY_SECTION_LEVEL", "catalog.groups[].groups[]"):
            ("sections", "linked-to-policy-section-level", "archer-select"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SECTION", "catalog.groups[].groups[]"):
            ("sections", "engagement-scope-in-control-section", "archer-select"),
        ("SOURCE_NAME", "catalog.groups[].groups[]"):
            ("sections", "source-name", "text"),
        ("LINKED_TO_POLICY_SUB_SECTION_LEVEL", "catalog.groups[].groups[].groups[]"):
            ("subsections", "linked-to-policy-sub-section-level", "archer-select"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SUB_SECTION", "catalog.groups[].groups[].groups[]"):
            ("subsections", "engagement-scope-in-control-sub-section", "archer-select"),
        ("SOURCE_NAME", "catalog.groups[].groups[].groups[]"):
            ("subsections", "source-name", "text"),
        ("SECTION_NAME", "catalog.groups[].groups[].groups[]"):
            ("subsections", "section-name", "text")}
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH")) in expected]
    if not rows:
        return {"status": "NOT_ENABLED", "owners": {},
                "scope": "No twelve-owner flag/label activation"}
    qa_check(len(rows) == 12
             and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]) for row in rows} == set(expected),
             "QA_EXACT_TWELVE_FLAG_LABEL_CONTRACTS_REQUIRED")
    for row in rows:
        field, owner = row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]
        lookup, name, transform = expected[(field, owner)]
        params = row.get("REPRESENTATION_PARAMS", {})
        target = owner if lookup is None else owner + ".props"
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else "props")
                 and row.get("TRANSFORM_ID") == transform
                 and params.get("joined_lookup") == lookup
                 and params.get("property_name") == name,
                 "QA_FLAG_LABEL_FIELD_AND_OWNER_CONTRACT_MISMATCH")
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = defaultdict(list)
    for key, (_, name, _) in expected.items():
        names[name].append(key)
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    def flag_label_family(prop):
        # These reviewed flags/labels are unqualified. A same-name property in a
        # separate nonempty namespace belongs to a different property family.
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and name in names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True)] if flag_label_family(payload) else []
        props = payload.get("props", [])
        qa_check(isinstance(props, list), "QA_PROPERTIES_MUST_BE_ARRAY")
        located.extend((prop, False) for prop in props
                       if isinstance(prop, dict) and flag_label_family(prop))
        for prop, standalone in located:
            candidates = names[prop["name"]]
            matching = [key for key in candidates if key[1] == owner]
            if len(matching) != 1:
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                continue
            field = matching[0]
            intended = field[1]
            lookup, _, _ = expected[field]
            metric = metrics[field]
            if standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            if set(prop) != {"name", "value"} or not isinstance(prop.get("value"), str):
                metric["invalid_property_shape"] += 1
            if isinstance(prop.get("value"), str):
                observed[field][(root, child)][prop["value"]] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (lookup, _, transform) in expected.items():
        owner = field[1]
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field[0])
            try:
                # Preserve exact labels/text; never convert No to a Boolean.
                desired = (qa_extension_text(raw) if transform == "text" else
                           qa_expected(raw, "archer-select", lookup is not None))
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired)
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    result = defaultdict(dict)
    for (field, owner), metric in metrics.items():
        result[owner][field] = dict(metric)
    return {"status": "CHECKED", "owners": dict(result),
            "scope": "Original owner flag/label parity only; no parent-title mutation or native entity/link claim"}


def qa_native_information_criticality(graph, source_input, load):
    """Check three exact pre-existing native rows without changing text semantics."""
    expected = {
        ("INFORMATION", "catalog.groups[].groups[]"):
            ("sections", "information", "text", "parts", "prose"),
        ("INFORMATION", "catalog.groups[].groups[].groups[]"):
            ("subsections", "information", "text", "parts", "prose"),
        ("SUBSECTION_CRITICALITY_VALUE", "catalog.groups[].groups[].groups[]"):
            ("subsections", "criticality-value", "direct", "props", "value"),
        ("INFORMATION", "catalog.groups[]"):
            ("topics", "information", "text", "parts", "prose"),
        ("SOURCE_CRITICALITY_VALUE", "catalog.metadata.props[]"):
            (None, "criticality-value", "direct", "props", "value"),
        ("TOPIC_CRITICALITY_VALUE", "catalog.groups[]"):
            ("topics", "criticality-value", "direct", "props", "value"),
        ("SECTION_CRITICALITY_VALUE", "catalog.groups[].groups[]"):
            ("sections", "criticality-value", "direct", "props", "value")}
    new_contracts = {
        ("INFORMATION", "catalog.groups[].groups[]"),
        ("INFORMATION", "catalog.groups[].groups[].groups[]"),
        ("SUBSECTION_CRITICALITY_VALUE", "catalog.groups[].groups[].groups[]")}
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH")) in expected]
    if not any((row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]) in new_contracts
               for row in rows):
        return {"status": "NOT_ENABLED", "owners": {}, "legacy_counterparts": {},
                "scope": "No three-native-field activation"}
    qa_check(len(rows) == 7
             and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]) for row in rows} == set(expected),
             "QA_EXACT_THREE_NATIVE_CONTRACTS_REQUIRED")
    for row in rows:
        field, owner = row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]
        lookup, name, transform, member, value_key = expected[(field, owner)]
        params = row.get("REPRESENTATION_PARAMS", {})
        target = owner if lookup is None else owner + "." + member
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else member)
                 and row.get("TRANSFORM_ID") == transform
                 and params.get("joined_lookup") == lookup
                 and params.get("property_name") == name,
                 "QA_NATIVE_FIELD_AND_OWNER_CONTRACT_MISMATCH")
    allow_nulls = {
        (row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]):
            (expected[(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"])][0] is None
             and row.get("REPRESENTATION_PARAMS", {}).get("preserve_null") is True)
        for row in rows}
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = defaultdict(list)
    for key, (_, name, _, member, _) in expected.items():
        names[(member, name)].append(key)
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    def native_family(prop, member):
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and (member, name) in names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True, "props")] if native_family(payload, "props") else []
        for member in ("props", "parts"):
            members = payload.get(member, [])
            qa_check(isinstance(members, list), "QA_NATIVE_MEMBERS_MUST_BE_ARRAY")
            located.extend((prop, False, member) for prop in members
                           if isinstance(prop, dict) and native_family(prop, member))
        for prop, standalone, member in located:
            candidates = names[(member, prop["name"])]
            matching = [key for key in candidates if key[1] == owner]
            if len(matching) != 1:
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                continue
            field = matching[0]
            intended = field[1]
            lookup, _, _, _, value_key = expected[field]
            metric = metrics[field]
            if standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            valid_value = (isinstance(prop.get(value_key), str)
                           or prop.get(value_key) is None and allow_nulls[field])
            if set(prop) != {"name", value_key} or not valid_value:
                metric["invalid_property_shape"] += 1
            if valid_value:
                observed[field][(root, child)][prop.get(value_key)] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (lookup, _, transform, _, _) in expected.items():
        owner = field[1]
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field[0])
            try:
                # Existing text trims outer whitespace and preserves HTML; direct keeps scalar text.
                if (raw is None and field[0] in original["object"] and allow_nulls[field]):
                    desired = Counter({None: 1})
                else:
                    desired = (qa_extension_text(raw) if transform == "text" else
                               qa_expected(raw, "direct", lookup is not None))
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired) and raw is not None
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    result, counterparts = defaultdict(dict), defaultdict(dict)
    for (field, owner), metric in metrics.items():
        target = result if (field, owner) in new_contracts else counterparts
        target[owner][field] = dict(metric)
    return {"status": "CHECKED", "owners": dict(result),
            "legacy_counterparts": dict(counterparts),
            "scope": "Three existing native contracts only; null samples do not prove populated warehouse acceptance"}



def qa_scalar_array_membership(raw):
    """Independently preserve distinct normalized finite scalar membership."""
    if raw is None:
        return Counter()
    if not isinstance(raw, list):
        raise ValueError("QA_SCALAR_ARRAY_REQUIRES_RAW_JSON_ARRAY")
    values = set()
    for value in raw:
        if type(value) not in (str, int, float, Decimal):
            raise ValueError("QA_SCALAR_ARRAY_REQUIRES_NONNULL_FLAT_SCALARS")
        text = qa_scalar(value)
        if text.lower() in {"infinity", "+infinity", "-infinity"}:
            raise ValueError("QA_SCALAR_ARRAY_REQUIRES_FINITE_NONBLANK_MEMBERS")
        values.add(text)
    return Counter({value: 1 for value in values})


def qa_scalar_array_source(record, context):
    """Match the compiled JSON-number parsing policy without calling transforms."""
    raw = record["CURATED_JSON"]
    options = context["compiled_plan"].get("options", {})
    if raw is None and options.get("null_source_as_empty"):
        return {}
    if isinstance(raw, str):
        raw = _qa_decode_json(raw, bool(options.get("parse_decimal")))
    if not isinstance(raw, dict):
        raise ValueError("QA_SCALAR_ARRAY_EXPECTED_JSON_OBJECT")
    return raw


def qa_owner_scalar_array_properties(graph, source_input, load):
    """Six exact opted-in original-owner fields; no entity/link/array-order claim."""
    expected = {
        ("CONTROL_PROCEDURES", "catalog.metadata.props[]"):
            (None, "control-procedures", "direct", "props", "value"),
        ("POLICIES_AUTHORITATIVE_SOURCE_REFERENCES", "catalog.metadata.props[]"):
            (None, "policies-authoritative-source-references", "direct", "props", "value"),
        ("CONTROL_PROCEDURES", "catalog.groups[]"):
            ("topics", "control-procedures", "direct", "props", "value"),
        ("CONTROL_PROCEDURES", "catalog.groups[].groups[]"):
            ("sections", "control-procedures", "direct", "props", "value"),
        ("CONTROL_PROCEDURES", "catalog.groups[].groups[].groups[]"):
            ("subsections", "control-procedures", "direct", "props", "value"),
        ("CONTROL_PROCEDURES_AUTHORITATIVE_SOURCES", "catalog.groups[].groups[].groups[]"):
            ("subsections", "control-procedures-authoritative-sources", "direct", "props", "value")}
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH")) in expected]
    spec = ctx["compiled_plan"].get("scalar_array_properties")
    if spec is None and not rows:
        return {"status": "NOT_ENABLED", "owners": {},
                "scope": "No six-scalar-array activation"}
    qa_check(isinstance(spec, dict)
             and set(spec) == {"release", "contracts"}
             and spec["release"] == "catalog-owner-scalar-array-props-review-v1"
             and isinstance(spec["contracts"], dict)
             and set(spec["contracts"]) == {owner+"|"+field for field,owner in expected},
             "QA_EXACT_SIX_SCALAR_ARRAY_DECLARATIONS_REQUIRED")
    qa_check(len(rows) == 6
             and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]) for row in rows} == set(expected),
             "QA_EXACT_SIX_SCALAR_ARRAY_CONTRACTS_REQUIRED")
    for row in rows:
        field, owner = row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]
        lookup, name, transform, member, value_key = expected[(field, owner)]
        params = row.get("REPRESENTATION_PARAMS", {})
        target = owner if lookup is None else owner + "." + member
        key = owner + "|" + field
        qa_check(spec["contracts"].get(key) == {
                    "enabled": True, "source_field": field, "owner_path": owner,
                    "joined_lookup": lookup, "property_name": name,
                    "value_shape": "strict-flat-scalar-array",
                    "value_encoding": "sorted-unique-scalar-text-membership"},
                 "QA_SCALAR_ARRAY_DECLARATION_DRIFT")
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else member)
                 and row.get("REPRESENTATION") == ("properties" if lookup is None else "joined-records")
                 and row.get("TRANSFORM_ID") == transform
                 and (row.get("VALUE_SOURCE") or "FIELD") == "FIELD"
                 and (row.get("NULL_POLICY") or "omit") == "omit"
                 and not row.get("LINEAGE_REQUIRED_FLAG")
                 and params.get("joined_lookup") == lookup
                 and params.get("property_name") == name
                 and not params.get("required") and not params.get("preserve_null")
                 and params.get("scalar_array_property_key") == key,
                 "QA_SCALAR_ARRAY_FIELD_AND_OWNER_CONTRACT_MISMATCH")
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_scalar_array_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_scalar_array_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = defaultdict(list)
    for key, (_, name, _, member, _) in expected.items():
        names[(member, name)].append(key)
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    family_names = {name for member, name in names}
    def array_family(prop, member):
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and name in family_names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True, "props")] if array_family(payload, "props") else []
        for member in ("props", "parts"):
            members = payload.get(member, [])
            qa_check(isinstance(members, list), "QA_NATIVE_MEMBERS_MUST_BE_ARRAY")
            located.extend((prop, False, member) for prop in members
                           if isinstance(prop, dict) and array_family(prop, member))
        for prop, standalone, member in located:
            candidates = names[("props", prop["name"])]
            if member != "props":
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                    metrics[key]["invalid_property_shape"] += 1
                continue
            matching = [key for key in candidates if key[1] == owner]
            if len(matching) != 1:
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                continue
            field = matching[0]
            intended = field[1]
            lookup, _, _, _, value_key = expected[field]
            metric = metrics[field]
            if standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            valid_value = isinstance(prop.get(value_key), str)
            if set(prop) != {"name", value_key} or not valid_value:
                metric["invalid_property_shape"] += 1
            if valid_value:
                observed[field][(root, child)][prop.get(value_key)] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (lookup, _, transform, _, _) in expected.items():
        owner = field[1]
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field[0])
            try:
                desired = qa_scalar_array_membership(raw)
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired) and raw is not None
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    result = defaultdict(dict)
    for (field, owner), metric in metrics.items():
        result[owner][field] = dict(metric)
    return {"status": "CHECKED", "owners": dict(result),
            "scope": "Distinct normalized membership at six original owners only; no order/multiplicity, native entity/link or populated warehouse acceptance claim"}


def qa_permissions_plan_fingerprint(context):
    """Recompute only retained compiled metadata; never call mapper/compiler APIs."""
    plan, mappings = context["compiled_plan"], context.get("mapping_rows")
    qa_check(isinstance(mappings, list) and plan.get("mappings") == mappings,
             "QA_COMPILED_MAPPING_ROWS_DRIFT")
    value = mappings
    native = plan.get("native_catalog")
    if native and native.get("guid_props"):
        value = {"mappings": mappings, "guid_props": native["guid_props"]}
    owner = plan.get("owner_procedure_props")
    if owner is not None:
        value = {"baseline": value, "owner_procedure_props": owner}
    arrays = plan.get("scalar_array_properties")
    if arrays is not None:
        value = {"baseline": value, "scalar_array_properties": arrays}
    fingerprint = hashlib.sha256(json.dumps(
        value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    qa_check(plan.get("mapping_fingerprint") == fingerprint,
             "QA_MAPPING_FINGERPRINT_CONTENT_MISMATCH")
    return fingerprint


def qa_permission_json_text_values(raw):
    """Match existing opaque json-text semantics without resolving permissions."""
    if qa_empty(raw):
        return Counter()
    try:
        encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("QA_PERMISSION_JSON_VALUE_NOT_SERIALIZABLE") from None
    return Counter({encoded: 1})


def qa_permission_source(record, context):
    """Parse retained input exactly under the compiled number/null policy."""
    raw = record["CURATED_JSON"]
    options = context["compiled_plan"].get("options", {})
    if raw is None and options.get("null_source_as_empty", False):
        return {}
    if isinstance(raw, str):
        raw = _qa_decode_json(raw, bool(options.get("parse_decimal", True)))
    if not isinstance(raw, dict):
        raise ValueError("QA_PERMISSION_EXPECTED_JSON_OBJECT")
    return raw


def qa_owner_permissions_properties(graph, source_input, load):
    """Four opaque JSON properties at original owners; no native-role inference."""
    expected = {
        ("DEFAULT_RECORD_PERMISSIONS", "catalog.metadata.props[]"):
            (None, "default-record-permissions", "json-text", "props", "value"),
        ("DEFAULT_RECORD_PERMISSIONS", "catalog.groups[]"):
            ("topics", "default-record-permissions", "json-text", "props", "value"),
        ("DEFAULT_RECORD_PERMISSIONS", "catalog.groups[].groups[]"):
            ("sections", "default-record-permissions", "json-text", "props", "value"),
        ("DEFAULT_RECORD_PERMISSIONS", "catalog.groups[].groups[].groups[]"):
            ("subsections", "default-record-permissions", "json-text", "props", "value")}
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if row.get("SOURCE_FIELD_NAME") == "DEFAULT_RECORD_PERMISSIONS"]
    qa_check(len(rows) == 4 and {
                 (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                 for row in rows} == set(expected),
             "QA_EXACT_FOUR_PERMISSION_CONTRACTS_REQUIRED")
    for row in rows:
        field, owner = row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]
        lookup, name, transform, member, value_key = expected[(field, owner)]
        target = owner if lookup is None else owner + "." + member
        parameters = {"property_name": name}
        if lookup is not None:
            parameters.update(target=member, joined_lookup=lookup)
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("CANONICAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else member)
                 and row.get("REPRESENTATION") == ("properties" if lookup is None else "joined-records")
                 and row.get("TRANSFORM_ID") == transform
                 and (row.get("VALUE_SOURCE") or "FIELD") == "FIELD"
                 and (row.get("NULL_POLICY") or "omit") == "omit"
                 and row.get("TRANSFORM_PARAMS") == {}
                 and row.get("REPRESENTATION_PARAMS") == parameters
                 and row.get("LINEAGE_REQUIRED_FLAG") is False,
                 "QA_PERMISSION_FIELD_AND_OWNER_CONTRACT_MISMATCH")
        qa_check(sum(
            other.get("OWNER_ELEMENT_PATH") == owner
            and other.get("REPRESENTATION_PARAMS", {}).get("property_name") == name
            for other in ctx["mapping_rows"]) == 1,
            "QA_PERMISSION_PROPERTY_HAS_ANOTHER_WRITER")
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_permission_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_permission_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = defaultdict(list)
    for key, (_, name, _, member, _) in expected.items():
        names[(member, name)].append(key)
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    family_names = {name for member, name in names}
    def permission_family(prop, member):
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and name in family_names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True, "props")] if permission_family(payload, "props") else []
        for member in ("props", "parts"):
            members = payload.get(member, [])
            qa_check(isinstance(members, list), "QA_NATIVE_MEMBERS_MUST_BE_ARRAY")
            located.extend((prop, False, member) for prop in members
                           if isinstance(prop, dict) and permission_family(prop, member))
        for prop, standalone, member in located:
            candidates = names[("props", prop["name"])]
            if member != "props":
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                    metrics[key]["invalid_property_shape"] += 1
                continue
            matching = [key for key in candidates if key[1] == owner]
            if len(matching) != 1:
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                continue
            field = matching[0]
            intended = field[1]
            lookup, _, _, _, value_key = expected[field]
            metric = metrics[field]
            if standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            valid_value = isinstance(prop.get(value_key), str)
            if set(prop) != {"name", value_key} or not valid_value:
                metric["invalid_property_shape"] += 1
            if valid_value:
                observed[field][(root, child)][prop.get(value_key)] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (lookup, _, transform, _, _) in expected.items():
        owner = field[1]
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field[0])
            try:
                desired = qa_permission_json_text_values(raw)
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired) and raw is not None
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    result = defaultdict(dict)
    for (field, owner), metric in metrics.items():
        result[owner][field] = dict(metric)
    return {"status": "CHECKED", "owners": dict(result),
            "scope": "Opaque sorted compact JSON at four original owners; existing empty-container omission retained, no permission-to-role conversion or native-role/persistence claim"}


def qa_owner_json184_expected():
    """Independent exact owner+raw-field matrix; all21 retained examples are NULL."""
    return {
        ("POLICY_LEVEL_3", "catalog.metadata.props[]"):
            (None, "policy-level-3", "json-text", "props", "value"),
        ("POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS", "catalog.metadata.props[]"):
            (None, "policy-level-3-from-topic-section-and-subsection-levels", "json-text", "props", "value"),
        ("COMPLIANCE_ENGAGEMENTS_SCOPE_PROCEDURES_FROM_SELECTED_AUTHORITATIVE_SOURCES", "catalog.metadata.props[]"):
            (None, "compliance-engagements-scope-procedures-from-selected-authoritative-sources", "json-text", "props", "value"),
        ("QUESTION_LIBRARY", "catalog.metadata.props[]"):
            (None, "question-library", "json-text", "props", "value"),
        ("DEVIATIONS_TOPICS_LINKED_HELPER", "catalog.groups[]"):
            ("topics", "deviations-topics-linked-helper", "json-text", "props", "value"),
        ("POLICY_LEVEL_3", "catalog.groups[]"):
            ("topics", "policy-level-3", "json-text", "props", "value"),
        ("POLICY_LEVEL_3_FROM_SECTION_AND_SUBSECTION_LEVELS", "catalog.groups[]"):
            ("topics", "policy-level-3-from-section-and-subsection-levels", "json-text", "props", "value"),
        ("QUESTION_LIBRARY", "catalog.groups[]"):
            ("topics", "question-library", "json-text", "props", "value"),
        ("DEVIATIONS_SECTIONS_LINKED_HELPER", "catalog.groups[].groups[]"):
            ("sections", "deviations-sections-linked-helper", "json-text", "props", "value"),
        ("POLICY_LEVEL_3", "catalog.groups[].groups[]"):
            ("sections", "policy-level-3", "json-text", "props", "value"),
        ("POLICY_LEVEL_3_FROM_SECTION_LEVEL_AND_BELOW", "catalog.groups[].groups[]"):
            ("sections", "policy-level-3-from-section-level-and-below", "json-text", "props", "value"),
        ("POLICIES_NEW_AUTH_SOURCE_CALC_CROSSREF_SECTION", "catalog.groups[].groups[]"):
            ("sections", "policies-new-auth-source-calc-crossref-section", "json-text", "props", "value"),
        ("POLICIES_COPY_OF_NEW_AUTH_SOURCE_CALC_CROSSREF_SECTION", "catalog.groups[].groups[]"):
            ("sections", "policies-copy-of-new-auth-source-calc-crossref-section", "json-text", "props", "value"),
        ("COMPLIANCE_ENGAGEMENTS_SCOPE_PROCEDURES_FROM_SELECTED_AUTHORITATIVE_SOURCES", "catalog.groups[].groups[]"):
            ("sections", "compliance-engagements-scope-procedures-from-selected-authoritative-sources", "json-text", "props", "value"),
        ("QUESTION_LIBRARY", "catalog.groups[].groups[]"):
            ("sections", "question-library", "json-text", "props", "value"),
        ("IMPLEMENTATION_STATEMENT", "catalog.groups[].groups[].groups[]"):
            ("subsections", "implementation-statement", "json-text", "props", "value"),
        ("ATO_GUIDANCE", "catalog.groups[].groups[].groups[]"):
            ("subsections", "ato-guidance", "json-text", "props", "value"),
        ("CONTROL_STANDARDS_ATCS_CONTROLS", "catalog.groups[].groups[].groups[]"):
            ("subsections", "control-standards-atcs-controls", "json-text", "props", "value"),
        ("POLICY_LEVEL_3", "catalog.groups[].groups[].groups[]"):
            ("subsections", "policy-level-3", "json-text", "props", "value"),
        ("POLICIES_NEW_AUTH_SOURCE_CALC_CROSSREF", "catalog.groups[].groups[].groups[]"):
            ("subsections", "policies-new-auth-source-calc-crossref", "json-text", "props", "value"),
        ("QUESTION_LIBRARY", "catalog.groups[].groups[].groups[]"):
            ("subsections", "question-library", "json-text", "props", "value")
    }


def qa_owner_business_json_properties(graph, source_input, load):
    """21 explicit opaque JSON field occurrences; no native/alias/link inference."""
    expected = qa_owner_json184_expected()
    ctx = graph["context"]
    rows = [row for row in ctx["mapping_rows"]
            if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH")) in expected]
    qa_check(len(rows) == 21 and {
                 (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                 for row in rows} == set(expected),
             "QA_EXACT_21_OWNER_JSON_CONTRACTS_REQUIRED")
    for row in rows:
        field, owner = row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"]
        lookup, name, transform, member, value_key = expected[(field, owner)]
        target = owner if lookup is None else owner + "." + member
        parameters = {"property_name": name}
        if lookup is not None:
            parameters.update(target=member, joined_lookup=lookup)
        qa_check(row.get("SOURCE_KEY") == "source-two-source"
                 and row.get("EXECUTION_STATUS") == "APPROVED"
                 and row.get("OWNER_ELEMENT_PATH") == owner
                 and row.get("OSCAL_ELEMENT_PATH") == target
                 and row.get("CANONICAL_ELEMENT_PATH") == target
                 and row.get("FIELD_RELATIVE_PATH") == ("" if lookup is None else member)
                 and row.get("REPRESENTATION") == ("properties" if lookup is None else "joined-records")
                 and row.get("TRANSFORM_ID") == transform
                 and (row.get("VALUE_SOURCE") or "FIELD") == "FIELD"
                 and (row.get("NULL_POLICY") or "omit") == "omit"
                 and row.get("TRANSFORM_PARAMS") == {}
                 and row.get("REPRESENTATION_PARAMS") == parameters
                 and row.get("LINEAGE_REQUIRED_FLAG") is False,
                 "QA_OWNER_JSON_FIELD_AND_OWNER_CONTRACT_MISMATCH")
        qa_check(sum(
            other.get("OWNER_ELEMENT_PATH") == owner
            and other.get("REPRESENTATION_PARAMS", {}).get("property_name") == name
            for other in ctx["mapping_rows"]) == 1,
            "QA_OWNER_JSON_PROPERTY_HAS_ANOTHER_WRITER")
    metrics = {field: qa_extension_metrics() for field in expected}
    for metric in metrics.values():
        metric["wrong_owner_occurrences"] = 0

    def identity(value):
        qa_check(value is not None and str(value).strip(), "QA_FROZEN_OWNER_ID_REQUIRED")
        return str(value).strip()

    source_docs = {}
    for record in qa_rows(source_input["source_df"]):
        identifier = identity(record["SOURCE_RECORD_ID"])
        qa_check(identifier not in source_docs, "QA_DUPLICATE_FROZEN_SOURCE")
        source_docs[identifier] = qa_permission_source(record, ctx)
    qa_check(len(source_docs) == source_input["selection"]["SELECTED_ROWS"] == load["source_records"],
             "QA_FROZEN_SOURCE_COUNT_MISMATCH")
    documents = {"catalog.metadata.props[]": {
        (identifier, identifier): {
            "object": obj, "chain": [("catalog.metadata", None), ("catalog", None)]}
        for identifier, obj in source_docs.items()}}
    lookups = ctx.get("lookups", {})
    joined, contracts = lookups.get("joined_sources", {}), lookups.get("joined_contract", {})
    qa_check(isinstance(joined, dict) and isinstance(contracts, dict),
             "QA_FROZEN_OWNER_FRAME_REQUIRED")
    group_paths = {"topics": "catalog.groups[]", "sections": "catalog.groups[].groups[]",
                   "subsections": "catalog.groups[].groups[].groups[]"}
    previous, owner_index = None, {}
    for binding in ("topics", "sections", "subsections"):
        qa_check(binding in joined and binding in contracts
                 and callable(getattr(joined[binding], "to_local_iterator", None))
                 and isinstance(contracts[binding], dict)
                 and contracts[binding].get("child_record_id_property") == "archer-content-id",
                 "QA_FROZEN_OWNER_FRAME_REQUIRED")
        records, owners = {}, {}
        for record in qa_rows(joined[binding]):
            child, parent_id = identity(record["_SOURCE_RECORD_ID"]), identity(record["CONTENT_ID"])
            qa_check(child not in records, "QA_DUPLICATE_FROZEN_OWNER")
            if previous is None:
                qa_check(parent_id in source_docs, "QA_FROZEN_OWNER_PARENT_MISSING")
                root, chain = parent_id, [("catalog", None)]
            else:
                qa_check(parent_id in owner_index[previous], "QA_FROZEN_OWNER_PARENT_MISSING")
                prior = owner_index[previous][parent_id]
                root, chain = prior["root"], [(group_paths[previous], parent_id)] + prior["chain"]
            records[child] = {"root": root, "chain": chain}
            owners[(root, child)] = {"object": qa_permission_source(record, ctx), "chain": chain}
        owner_index[binding] = records
        documents[group_paths[binding]] = owners
        previous = binding

    node_rows = list(qa_rows(graph["nodes"]))
    nodes = {node["NODE_KEY"]: node for node in node_rows}
    qa_check(len(nodes) == len(node_rows), "QA_DUPLICATE_PREVIEW_NODE_KEY")
    parents = qa_parent_index(graph)
    table = ctx["config"]["SOURCE_TABLE_NAME"]
    def parent_of(node):
        keys = parents[node["NODE_KEY"]]
        return nodes.get(keys[0]) if len(keys) == 1 else None
    @_qa_compact_provenance
    def provenance(node):
        props = qa_payload(node).get("props", [])
        qa_check(isinstance(props, list), "QA_GROUP_PROPERTIES_MUST_BE_ARRAY")
        values = [prop.get("value") for prop in props
                  if isinstance(prop, dict) and prop.get("name") == "archer-content-id"]
        return values[0] if len(values) == 1 and isinstance(values[0], str) and values[0] else None
    names = defaultdict(list)
    for key, (_, name, _, member, _) in expected.items():
        names[(member, name)].append(key)
    observed = {field: defaultdict(Counter) for field in expected}
    groups = defaultdict(list)
    family_names = {name for member, name in names}
    def permission_family(prop, member):
        name, namespace = prop.get("name"), prop.get("ns")
        return (isinstance(name, str) and name in family_names
                and not (isinstance(namespace, str) and namespace.strip()))
    for node in nodes.values():
        owner = node["ELEMENT_PATH"]
        if owner in group_paths.values():
            child = provenance(node)
            if child is not None:
                groups[(owner, str(node["SOURCE_RECORD_ID"]), child)].append(node)
        payload = qa_payload(node)
        located = [(payload, True, "props")] if permission_family(payload, "props") else []
        for member in ("props", "parts"):
            members = payload.get(member, [])
            qa_check(isinstance(members, list), "QA_NATIVE_MEMBERS_MUST_BE_ARRAY")
            located.extend((prop, False, member) for prop in members
                           if isinstance(prop, dict) and permission_family(prop, member))
        for prop, standalone, member in located:
            candidates = names[("props", prop["name"])]
            if member != "props":
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                    metrics[key]["invalid_property_shape"] += 1
                continue
            matching = [key for key in candidates if key[1] == owner]
            if len(matching) != 1:
                for key in candidates:
                    metrics[key]["wrong_owner_occurrences"] += 1
                continue
            field = matching[0]
            intended = field[1]
            lookup, _, _, _, value_key = expected[field]
            metric = metrics[field]
            if standalone != (lookup is None):
                metric["wrong_owner_occurrences"] += 1
                continue
            root = str(node["SOURCE_RECORD_ID"])
            child = root if standalone else provenance(node)
            if child is None:
                metric["ownership_errors"] += 1
                continue
            if node["SOURCE_TABLE_NAME"] != table:
                metric["ownership_errors"] += 1
            valid_value = isinstance(prop.get(value_key), str)
            if set(prop) != {"name", value_key} or not valid_value:
                metric["invalid_property_shape"] += 1
            if valid_value:
                observed[field][(root, child)][prop.get(value_key)] += 1
            if standalone:
                current = node
                for path, _ in documents[intended].get((root, child), {}).get("chain", []):
                    parent = parent_of(current)
                    metric["ownership_errors"] += int(not (
                        parent is not None and parent["ELEMENT_PATH"] == path
                        and str(parent["SOURCE_RECORD_ID"]) == root
                        and parent["SOURCE_TABLE_NAME"] == table))
                    if parent is None:
                        break
                    current = parent
    for field, (lookup, _, transform, _, _) in expected.items():
        owner = field[1]
        metric = metrics[field]
        for key, original in documents[owner].items():
            root, child = key
            if lookup is not None:
                matches = groups.get((owner, root, child), [])
                metric["ownership_errors"] += int(len(matches) != 1)
                for node in matches:
                    metric["ownership_errors"] += int(node["SOURCE_TABLE_NAME"] != table)
                    current = node
                    for path, expected_id in original["chain"]:
                        parent = parent_of(current)
                        valid = (parent is not None and parent["ELEMENT_PATH"] == path
                                 and str(parent["SOURCE_RECORD_ID"]) == root
                                 and parent["SOURCE_TABLE_NAME"] == table)
                        if valid and expected_id is not None:
                            valid = provenance(parent) == expected_id
                        metric["ownership_errors"] += int(not valid)
                        if parent is None:
                            break
                        current = parent
            actual = observed[field].pop(key, Counter())
            metric["source_records"] += 1
            metric["actual_values"] += sum(actual.values())
            raw = original["object"].get(field[0])
            try:
                desired = qa_permission_json_text_values(raw)
            except (ValueError, TypeError, ArithmeticError):
                metric["normalization_review"] += 1
                continue
            metric["populated_source_records"] += bool(desired) and raw is not None
            metric["expected_values"] += sum(desired.values())
            metric["missing_values"] += sum((desired - actual).values())
            metric["unexpected_values"] += sum((actual - desired).values())
            metric["exact_records"] += desired == actual
        metric["orphan_property_values"] += sum(
            sum(counter.values()) for counter in observed[field].values())
    result = defaultdict(dict)
    for (field, owner), metric in metrics.items():
        result[owner][field] = dict(metric)
    return {"status": "CHECKED", "owners": dict(result),
            "scope": "Opaque sorted compact JSON for21 original field occurrences; retained samples establish NULL omission only, positive generic-JSON fixtures are supplemental; no native entity/link/role/event/alias/calculation or persistence claim"}


def _run_source_two_owner_json184_value_qa(model_graphs, source_inputs, pipeline_report, detail_limit=5):
    MODEL_GRAPHS, SOURCE_INPUTS, PIPELINE_REPORT = model_graphs, source_inputs, pipeline_report
    qa_check(type(detail_limit) is int and 0 <= detail_limit <= 5, "QA_DETAIL_LIMIT_ZERO_TO_FIVE")
    routes = {("source-two-source", "CATALOG"): 93,
              ("source-two-topic", "ASSESSMENT_RESULTS"): 7,
              ("source-two-section", "ASSESSMENT_RESULTS"): 10,
              ("source-two-subsection", "ASSESSMENT_RESULTS"): 16}
    qa_check(isinstance(MODEL_GRAPHS, dict) and set(MODEL_GRAPHS) == set(routes),
             "QA_EXPECTED_FOUR_SPRINT_ROUTES")
    catalog_route = ("source-two-source", "CATALOG")
    catalog_context = MODEL_GRAPHS[catalog_route].get("context")
    qa_check(isinstance(catalog_context, dict)
             and isinstance(catalog_context.get("compiled_plan"), dict),
             "QA_COMPILED_CATALOG_CONTEXT_REQUIRED")
    if catalog_context["compiled_plan"].get("owner_procedure_props") is not None:
        routes[catalog_route] = 97
    policy_fields = {
        "NUMBER_OF_POLICIES_SOURCE_LEVEL", "NUMBER_OF_POLICIES_TOPIC_LEVEL",
        "TOTAL_NUMBER_OF_SECTIONS_LINKED_TO_POLICY", "PERCENT_OF_SECTIONS_LINKED_TO_POLICY",
        "NUMBER_OF_POLICIES_SECTION_LEVEL", "TOTAL_NUMBER_OF_SUB_SECTIONS_LINKED_TO_POLICY",
        "PERCENT_OF_SUB_SECTIONS_LINKED_TO_POLICY", "NUMBER_OF_POLICIES_SUB_SECTION_LEVEL"}
    policy_rows = [row for row in catalog_context.get("mapping_rows", [])
                   if row.get("SOURCE_FIELD_NAME") in policy_fields]
    if policy_rows:
        qa_check(len(policy_rows) == 8
                 and {row["SOURCE_FIELD_NAME"] for row in policy_rows} == policy_fields,
                 "QA_EXACT_EIGHT_POLICY_CONTRACTS_REQUIRED")
        routes[catalog_route] += 8
    flag_label_identities = {
        ("LINKED_TO_POLICY_SOURCE_LEVEL", "catalog.metadata.props[]"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SOURCE", "catalog.metadata.props[]"),
        ("LINKED_TO_POLICY_TOPIC_LEVEL", "catalog.groups[]"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_TOPIC", "catalog.groups[]"),
        ("SOURCE_NAME_CALC_FIELD", "catalog.groups[]"),
        ("LINKED_TO_POLICY_SECTION_LEVEL", "catalog.groups[].groups[]"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SECTION", "catalog.groups[].groups[]"),
        ("SOURCE_NAME", "catalog.groups[].groups[]"),
        ("LINKED_TO_POLICY_SUB_SECTION_LEVEL", "catalog.groups[].groups[].groups[]"),
        ("ENGAGEMENT_SCOPE_IN_CONTROL_SUB_SECTION", "catalog.groups[].groups[].groups[]"),
        ("SOURCE_NAME", "catalog.groups[].groups[].groups[]"),
        ("SECTION_NAME", "catalog.groups[].groups[].groups[]")}
    flag_label_rows = [row for row in catalog_context.get("mapping_rows", [])
                       if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                       in flag_label_identities]
    if flag_label_rows:
        qa_check(routes[catalog_route] == 105, "QA_150_REQUIRES_CURRENT138_BASE")
        qa_check(len(flag_label_rows) == 12
                 and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"])
                      for row in flag_label_rows} == flag_label_identities,
                 "QA_EXACT_TWELVE_FLAG_LABEL_CONTRACTS_REQUIRED")
        routes[catalog_route] += 12
    native_identities = {
        ("INFORMATION", "catalog.groups[].groups[]"),
        ("INFORMATION", "catalog.groups[].groups[].groups[]"),
        ("SUBSECTION_CRITICALITY_VALUE", "catalog.groups[].groups[].groups[]")}
    native_rows = [row for row in catalog_context.get("mapping_rows", [])
                   if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                   in native_identities]
    if native_rows:
        qa_check(routes[catalog_route] == 117, "QA_153_REQUIRES_CURRENT150_BASE")
        qa_check(len(native_rows) == 3
                 and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"])
                      for row in native_rows} == native_identities,
                 "QA_EXACT_THREE_NATIVE_CONTRACTS_REQUIRED")
        routes[catalog_route] += 3
    array_identities = {
        ("CONTROL_PROCEDURES", "catalog.metadata.props[]"),
        ("POLICIES_AUTHORITATIVE_SOURCE_REFERENCES", "catalog.metadata.props[]"),
        ("CONTROL_PROCEDURES", "catalog.groups[]"),
        ("CONTROL_PROCEDURES", "catalog.groups[].groups[]"),
        ("CONTROL_PROCEDURES", "catalog.groups[].groups[].groups[]"),
        ("CONTROL_PROCEDURES_AUTHORITATIVE_SOURCES", "catalog.groups[].groups[].groups[]")}
    array_rows = [row for row in catalog_context.get("mapping_rows", [])
                  if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                  in array_identities]
    if array_rows or catalog_context["compiled_plan"].get("scalar_array_properties") is not None:
        qa_check(routes[catalog_route] == 120, "QA_159_REQUIRES_CURRENT153_BASE")
        qa_check(len(array_rows) == 6
                 and {(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"])
                      for row in array_rows} == array_identities,
                 "QA_EXACT_SIX_SCALAR_ARRAY_CONTRACTS_REQUIRED")
        routes[catalog_route] += 6
    permission_rows = [row for row in catalog_context.get("mapping_rows", [])
                       if row.get("SOURCE_FIELD_NAME") == "DEFAULT_RECORD_PERMISSIONS"]
    qa_check(routes[catalog_route] == 126 and len(permission_rows) == 4,
             "QA_163_REQUIRES_CURRENT159_AND_FOUR_PERMISSION_RULES")
    routes[catalog_route] += 4
    owner_json_expected = qa_owner_json184_expected()
    owner_json_rows = [row for row in catalog_context.get("mapping_rows", [])
                       if (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                       in owner_json_expected]
    qa_check(len(owner_json_rows) == 21 and {
                 (row.get("SOURCE_FIELD_NAME"), row.get("OWNER_ELEMENT_PATH"))
                 for row in owner_json_rows} == set(owner_json_expected),
             "QA_184_REQUIRES_EXACT_21_ADDITIONAL_OWNER_JSON_RULES")
    qa_check(catalog_context["compiled_plan"].get("options", {}).get("parse_decimal") is False,
             "QA_OWNER_JSON_REQUIRES_COMPILED_NUMBER_POLICY")
    routes[catalog_route] += 21
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
        fingerprint = qa_permissions_plan_fingerprint(ctx)
        qa_check(isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None
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
    _qa_phase("child-assessment-values", "STARTED")
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
    
    _qa_phase("child-assessment-values", "COMPLETED")
    route = ("source-two-source", "CATALOG")
    graph = MODEL_GRAPHS[route]
    ctx = graph["context"]
    _qa_phase("owner-procedure-values", "STARTED")
    owner_procedures = qa_owner_procedure_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("owner-procedure-values", "COMPLETED")
    _qa_phase("policy-scalar-values", "STARTED")
    policy_scalars = qa_policy_scalar_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("policy-scalar-values", "COMPLETED")
    _qa_phase("owner-flag-and-label-values", "STARTED")
    flag_labels = qa_owner_flag_label_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("owner-flag-and-label-values", "COMPLETED")
    _qa_phase("native-information-and-criticality", "STARTED")
    native_fields = qa_native_information_criticality(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("native-information-and-criticality", "COMPLETED")
    _qa_phase("scalar-array-values", "STARTED")
    scalar_arrays = qa_owner_scalar_array_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("scalar-array-values", "COMPLETED")
    _qa_phase("permissions-json-values", "STARTED")
    permissions = qa_owner_permissions_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("permissions-json-values", "COMPLETED")
    _qa_phase("owner-business-json-values", "STARTED")
    owner_json = qa_owner_business_json_properties(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("owner-business-json-values", "COMPLETED")
    _qa_phase("catalog-extension-values", "STARTED")
    catalog_extensions = qa_catalog_extensions(
        graph, SOURCE_INPUTS[route[0]], groups[route]["load"])
    _qa_phase("catalog-extension-values", "COMPLETED")
    _qa_phase("native-control-associations-and-statements", "STARTED")
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
    parents = qa_parent_index(graph)
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
    errors += sum(metric.get(key, 0) for metric in owner_procedures["owners"].values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for metric in policy_scalars["fields"].values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for fields in flag_labels["owners"].values()
                  for metric in fields.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for collection in ("owners", "legacy_counterparts")
                  for fields in native_fields[collection].values()
                  for metric in fields.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for fields in scalar_arrays["owners"].values()
                  for metric in fields.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for fields in permissions["owners"].values()
                  for metric in fields.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    errors += sum(metric.get(key, 0) for fields in owner_json["owners"].values()
                  for metric in fields.values()
                  for key in ("normalization_review", "missing_values", "unexpected_values",
                              "ownership_errors", "invalid_property_shape",
                              "wrong_owner_occurrences", "orphan_property_values"))
    _qa_phase("native-control-associations-and-statements", "COMPLETED")
    return {"owner_json_properties": owner_json,
            "default_record_permissions": permissions,
            "scalar_array_properties": scalar_arrays,
            "native_information_criticality": native_fields,
            "owner_flag_label_properties": flag_labels,
            "policy_scalar_properties": policy_scalars,
            "owner_procedure_properties": owner_procedures,
            "catalog_extension_properties": catalog_extensions,
            "child_assessment_results": child_summaries,
            "procedure_by_control_path": procedure_summary,
            "catalog_standard_associations": association_summary,
            "missing_statement_classification": statement_summary,
            "statement_content_scope": "Full id/title/statement equality already passed the mapper frozen-field check; this QA classifies omission occurrences",
            "missing_statement_id_details_private": statement_details,
            "error_count": errors,
            "result": "PASS" if errors == 0 else "REVIEW_REQUIRED",
            "scope": "Frozen preview parity only; no persistence/full-document-conformance claim"}

def run_source_two_owner_json184_value_qa(
        model_graphs, source_inputs, pipeline_report, detail_limit=5,
        progress_callback=None):
    """Audit one frozen184 preview; reuse is scoped and never changes acceptance."""
    qa_check(_QA_AUDIT_REUSE.get() is None, "QA_AUDIT_ALREADY_ACTIVE")
    qa_check(progress_callback is None or callable(progress_callback),
             "QA_PROGRESS_CALLBACK_MUST_BE_CALLABLE")
    scope = _QaAuditReuseScope(progress_callback)
    token = _QA_AUDIT_REUSE.set(scope)
    try:
        return _run_source_two_owner_json184_value_qa(
            model_graphs, source_inputs, pipeline_report, detail_limit)
    finally:
        try:
            scope.close()
        finally:
            _QA_AUDIT_REUSE.reset(token)


qa_session_names = ("MODEL_GRAPHS", "SOURCE_INPUTS", "PIPELINE_REPORT")
qa_session_present = [name for name in qa_session_names if name in globals()]
if __name__ == "__main__" or qa_session_present:
    if len(qa_session_present) != len(qa_session_names):
        raise RuntimeError("QA_PREVIEW_SESSION_REQUIRED")
    SOURCE_TWO_OWNER_JSON184_VALUE_QA = run_source_two_owner_json184_value_qa(
        MODEL_GRAPHS, SOURCE_INPUTS, PIPELINE_REPORT,
        progress_callback=lambda phase, state: print("QA phase: " + phase + " " + state, flush=True))
    print("SOURCE_TWO_OWNER_JSON184_PREVIEW_VALUE_QA")
    print(json.dumps(SOURCE_TWO_OWNER_JSON184_VALUE_QA, indent=2, default=str))
    if SOURCE_TWO_OWNER_JSON184_VALUE_QA["error_count"]:
        raise RuntimeError("QA_VALUE_OR_OWNERSHIP_REVIEW_REQUIRED")
