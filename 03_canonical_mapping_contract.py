# %% Cell 3 - Compile the mapping CSV against the element registry (zero hardcoded field counts)

import copy
import hashlib
import json
import math
import re
from collections import Counter

LEAN_MAPPER_RELEASE = "lean-csv-registry-v18-native-catalog-bulk"
METADATA_TRANSFORM_IDS = {
    "direct", "text", "prose-direct", "timestamp", "date", "identifier", "archer-select",
    "scalar-score", "security-objective", "status-crosswalk", "reject-populated", "oscal-scoped-group-id",
    "skip", "canonical-text", "reference-ids", "json-text", "json-value", "oscal-token",
    "catalog-related-subsections", "catalog-source-links", "prose-or-link-array", "archer-guid-procedure-props",
    "catalog-owner-procedure-props", "catalog-record-reference", "resource-base64", "resource-citation", "scalar-array",
}
METADATA_INSTANCE_RULES = {
    "record": "SOURCE_RECORD_ID", "optional-record": "SOURCE_RECORD_ID", "observations": "SOURCE_FIELD_NAME",
    "inline-links": "SOURCE_FIELD_NAME+LINK_ID", "properties": "SOURCE_FIELD_NAME+VALUE", "named-parts": "PART_NAME", "values": "VALUE", "references": "CONTENT_ID",
    "roles": "SOURCE_FIELD_NAME", "parties": "ID", "assignments": "SOURCE_FIELD_NAME+ID",
    "catalog-controls": "CONTENT_ID", "catalog-resources": "RESOURCE_ID",
}
METADATA_ITEM_PATHS = {
    operator: (None if operator in {"record", "optional-record", "observations"} else
               "UserList[]" if operator in {"parties", "assignments"} else "$")
    for operator in METADATA_INSTANCE_RULES
}
NATIVE_CATALOG_OWNER_PATHS = (
    "catalog", "catalog.groups[]", "catalog.groups[].groups[]",
    "catalog.groups[].groups[].groups[]",
)
OWNER_PROCEDURE_PROPERTY_RELEASE = "catalog-owner-procedure-props-review-v1"
SCALAR_ARRAY_PROPERTY_RELEASE = "catalog-owner-scalar-array-props-review-v1"


def _meta_row(row):
    row = row.as_dict(recursive=True) if hasattr(row, "as_dict") else row
    result = {}
    for key, value in row.items():
        key = str(key).strip().upper()
        key = {"ARCHER_FIELD_NAME": "SOURCE_FIELD_NAME", "MAPPING_STATUS": "STATUS"}.get(key, key)
        if key in result:
            raise ValueError("Ambiguous metadata column: " + key)
        result[key] = (None if value is None or isinstance(value, float) and math.isnan(value)
                       else value.strip() if isinstance(value, str) else value)
    return result


def _metadata_column_text(row, key, required=False):
    value = row.get(key)
    if value in (None, "") and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(key + " must contain nonblank text")
    return value.strip()


def _metadata_items(row, key):
    value = _metadata_column_text(row, key)
    items = [item.strip() for item in value.split("|")] if value else []
    if any(not item for item in items) or len(set(items)) != len(items):
        raise ValueError(key + " contains empty or duplicate entries")
    return items


def _registry_meta_bool(row, key):
    value = row.get(key)
    if type(value) is bool:
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError(key + " must be true or false")


def _registry_path(row):
    return row.get("NODE_PATH") or ""


def _registry_model(row):
    return str(row.get("OSCAL_MODEL_KEY") or "").upper()


def _model_token(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _metadata_params(row):
    return row.get("REPRESENTATION_PARAMS") or {}


def _metadata_target(row):
    return _metadata_params(row).get("target") or row.get("FIELD_RELATIVE_PATH") or row.get("OSCAL_FIELD_NAME")


def _lineage_required(row):
    value = str(row.get("LINEAGE_REQUIRED") or "N").strip().upper()
    if value not in {"Y", "N"}:
        raise ValueError("LINEAGE_REQUIRED must be Y or N")
    return value == "Y"


def _owner_for_path(path, paths):
    return max((p for p in paths if path == p or path.startswith(p + ".")), key=len, default=None)


def _scalar_array_property_key(field, owner):
    return owner + "|" + field


def _registry_operator(row):
    operator = _metadata_column_text(row, "OPERATOR")
    if operator:
        if operator not in {"object", "joined-records", *METADATA_INSTANCE_RULES}:
            raise ValueError("Unknown registry OPERATOR")
        return operator
    if not _registry_meta_bool(row, "IS_COLLECTION"):
        return "object"
    identity = (row.get("INSTANCE_KEY_RULE"), _metadata_column_text(row, "ITEM_PATH"))
    if identity == ("LINK_ID", "$"):
        return "catalog-resources"
    for candidate in METADATA_INSTANCE_RULES:
        if identity == (METADATA_INSTANCE_RULES[candidate], METADATA_ITEM_PATHS[candidate]):
            return candidate
    raise ValueError("Collection requires a supported registry OPERATOR and identity")


def _registry_elements(rows, selected, route, model, link_contracts=None):
    """Validate hierarchy once, retaining mapped/explicit paths and their ancestors."""
    by_path = {_registry_path(row): row for row in rows}
    if not by_path or "" in by_path or len(by_path) != len(rows):
        raise ValueError("Enabled model requires unique active registry paths")
    parents = {path: row.get("PARENT_NODE_PATH") or None for path, row in by_path.items()}
    roots = [path for path, parent in parents.items() if parent is None]
    if len(roots) != 1 or "." in roots[0]:
        raise ValueError("Enabled model requires one registry root")
    root = roots[0]
    for path, row in by_path.items():
        order = row.get("PROCESS_ORDER")
        order = 0 if order in (None, "") else order
        if isinstance(order, bool) or int(order) != float(order):
            raise ValueError("Registry PROCESS_ORDER must be an integer")
        row["PROCESS_ORDER"] = int(order)
        if _registry_meta_bool(row, "IS_COLLECTION") != path.endswith("[]"):
            raise ValueError("Registry collection flag conflicts with its path")
        if path != root and (parents[path] not in by_path or not path.startswith(parents[path] + ".")):
            raise ValueError("Registry child requires its active path ancestor")
    included = {root} | {row["OWNER_ELEMENT_PATH"] for row in selected}
    included.update(path for path, row in by_path.items() if row.get("OPERATOR"))
    groups, linked = [], set()
    for path in sorted(included):
        if _registry_operator(by_path[path]) != "assignments":
            continue
        siblings = {"roles": [], "parties": []}
        for other, row in by_path.items():
            if parents[other] != parents[path]:
                continue
            try:
                operator = _registry_operator(row)
            except ValueError:
                if row.get("OPERATOR"):
                    raise
                continue
            if operator in siblings:
                siblings[operator].append(other)
        if any(len(paths) != 1 for paths in siblings.values()):
            raise ValueError("Assignment requires one role and one party registry sibling")
        role, party = siblings["roles"][0], siblings["parties"][0]
        if {path, role, party} & linked:
            raise ValueError("Reference families require distinct registry paths")
        linked.update((path, role, party))
        groups.append({
            "roles_path": role, "parties_path": party, "assignments_path": path,
            "party_type": "person",
            "source_namespace": {
                "SOURCE_SYSTEM_NAME": route["source_system"],
                "SOURCE_TABLE_NAME": route["source_identity"],
                "MODEL_KEY": model,
            },
        })
    included.update(linked)
    for path in tuple(included):
        parent = parents[path]
        while parent is not None and parent not in included:
            included.add(parent)
            parent = parents[parent]
    elements = {}
    for path in sorted(included):
        row, parent = by_path[path], parents[path]
        operator, collection = _registry_operator(row), _registry_meta_bool(row, "IS_COLLECTION")
        if operator != "object" and not collection:
            raise ValueError("Collection operator requires IS_COLLECTION=true")
        parameters = {"registry_contract": {"parent_path": parent, "is_collection": collection}}
        if collection:
            identity = (row.get("INSTANCE_KEY_RULE"), _metadata_column_text(row, "ITEM_PATH"))
            if operator == "joined-records":
                if not identity[0] or identity[1] != "$":
                    raise ValueError("Joined-record collection requires an identity source field and ITEM_PATH=$")
                parameters["joined_instance_field"] = identity[0]
            else:
                expected = ("VALUE", "$") if operator == "object" else (METADATA_INSTANCE_RULES[operator], METADATA_ITEM_PATHS[operator])
                if identity != expected and not (operator == "properties" and identity == ("SOURCE_FIELD_NAME", "$")) and not (operator == "catalog-resources" and identity == ("LINK_ID", "$")):
                    raise ValueError("Registry identity conflicts with OPERATOR")
            parameters["registry_contract"].update(instance_key_rule=identity[0], item_path=identity[1])
        if parent and _registry_meta_bool(by_path[parent], "IS_COLLECTION"):
            parent_operator = _registry_operator(by_path[parent])
            if parent_operator in {"record", "optional-record", "joined-records"}:
                parameters["parent_instance_rule"] = "source-record"
            elif not (parent_operator == "references" and operator == "properties"):
                raise ValueError("Nested collection requires an identity-bearing collection parent")
        elif operator in {"record", "optional-record", "joined-records"}:
            parameters["parent_instance_rule"] = "singleton"
        policy = _metadata_column_text(row, "UUID_POLICY", required=bool(row.get("OPERATOR"))) or "omit"
        if policy not in {"omit", "node", "instance"} or (policy == "instance") != (operator == "parties"):
            raise ValueError("Invalid registry UUID policy")
        if policy != "omit":
            parameters["include_uuid"] = True
        if policy == "instance":
            parameters["uuid_from_instance"] = True
        members = _metadata_items(row, "REQUIRED_MEMBERS")
        if members:
            invalid_member = any(not re.fullmatch(r"[\w-]+(?:\.[\w-]+)*", member) for member in members)
            if invalid_member or operator not in {"object", "joined-records", "catalog-controls"} or (operator == "object" and collection):
                raise ValueError("REQUIRED_MEMBERS requires scalar object or joined-record member paths")
            parameters["required_members"] = members
            if operator == "object":
                parameters["optional_assembly"] = True
                native_rows = [
                    item for item in selected
                    if item["OWNER_ELEMENT_PATH"] == path
                    and item["FIELD_RELATIVE_PATH"] in members
                    and item.get("EXECUTION_STATUS") == "APPROVED"
                ]
                if (native_rows
                        and {item["FIELD_RELATIVE_PATH"] for item in native_rows} == set(members)
                        and all(item.get("NULL_POLICY") == "preserve" for item in native_rows)):
                    parameters["preserve_explicit_null_members"] = True
        elif operator == "object" and not collection:
            parameters["materialize_empty"] = True
        if operator == "inline-links":
            contract = (link_contracts or {}).get(path)
            expected = {"id_key", "name_key", "href_key", "order_key", "rel", "include_text", "allowed_schemes"}
            if (not path.endswith(".links[]") or not isinstance(contract, dict) or set(contract) != expected
                    or any(not isinstance(contract[k], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", contract[k])
                           for k in ("id_key", "name_key", "href_key", "order_key"))
                    or len({contract[k] for k in ("id_key", "name_key", "href_key", "order_key")}) != 4
                    or not isinstance(contract["rel"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9._-]*", contract["rel"])
                    or type(contract["include_text"]) is not bool
                    or not isinstance(contract["allowed_schemes"], list) or not contract["allowed_schemes"]
                    or any(x not in {"http", "https"} for x in contract["allowed_schemes"])
                    or policy != "omit"):
                raise ValueError("Inline links require a declared native link projection contract")
            parameters["inline_link_contract"] = copy.deepcopy(contract)
        if operator == "named-parts":
            names = [item.get("PROPERTY_NAME") for item in selected if item.get("OWNER_ELEMENT_PATH") == path]
            if len(names) != len(set(names)):
                raise ValueError("Named part ownership is ambiguous")
        if operator in {"properties", "observations"}:
            parameters["property_name_rule"] = "source-field-slug"
        if operator in {"roles", "parties"} and path not in linked:
            raise ValueError("Linked identity operator lacks an assignment family")
        elements[path] = {"operator": operator, "parameters": parameters}
    if elements[root]["operator"] != "object":
        raise ValueError("Registry root requires an object operator")
    # An explicit forward binding may add members beside a retained local record.
    # The registry and unqualified CSV rows keep their original local ownership.
    for binding, contract in route.get("joined_lookups", {}).items():
        if not {"append_to_record_path", "missing_member_policy"}.intersection(contract):
            continue
        path = contract.get("append_to_record_path")
        if (not isinstance(path, str) or path not in elements
                or elements[path]["operator"] != "record"
                or contract.get("projection") not in {"forward-raw-physical-v1", "forward-raw-physical-v2"}
                or contract.get("missing_member_policy") != "omit"
                or not isinstance(contract.get("instance_field"), str) or not contract["instance_field"].strip()
                or "joined-records" not in route.get("lookup_groups", ())):
            raise ValueError("Appended forward members require an explicit record path and lookup contract")
        owned = [item for item in selected if item.get("LOOKUP_KEY") == binding]
        if not owned or any(item["OWNER_ELEMENT_PATH"] != path for item in owned):
            raise ValueError("Appended lookup must own mappings at exactly its declared record path")
        elements[path]["parameters"].setdefault("record_joined_bindings", {})[binding] = contract["instance_field"]
    return root, [row for row in rows if _registry_path(row) in included], elements, groups


def _compile_resource_member_mapping(row, elements):
    target = {"resource-base64": "base64", "resource-citation": "citation"}[row["TRANSFORM_ID"]]
    if (row["FIELD_RELATIVE_PATH"] != target or not row["SOURCE_FIELD_NAME"]
            or row["EXECUTION_STATUS"] != "APPROVED"
            or (row.get("VALUE_SOURCE") or "FIELD") != "FIELD"
            or (row.get("NULL_POLICY") or "omit") != "omit"
            or _lineage_required(row)
            or elements[row["OWNER_ELEMENT_PATH"]]["parameters"]["registry_contract"]["instance_key_rule"] != "RESOURCE_ID"
            or any(row.get(name) not in (None, "") for name in (
                "PROPERTY_NAME", "VALUE_REQUIRED", "ALLOWED_VALUES", "VALUE_MAP",
                "OTHER_REMARKS_TEMPLATE", "ROLE_ID", "ROLE_TITLE", "DESCRIPTION_REQUIRED"))):
        raise ValueError("Resource member mapping requires an explicit approved field contract")
    params = {"source_field": row["SOURCE_FIELD_NAME"], "target": target}
    lookup = _metadata_column_text(row, "LOOKUP_KEY")
    if target == "citation":
        level = _metadata_column_text(row, "REFERENCE_TYPE", True)
        if not lookup or not level.isascii() or not level.isdecimal() or int(level) <= 0 or str(int(level)) != level:
            raise ValueError("Resource citation requires a lookup and canonical positive reference level")
        params.update(resource_lookup=lookup, reference_level=int(level))
    elif row.get("REFERENCE_TYPE") not in (None, ""):
        raise ValueError("Base64 resource cannot declare a reference type")
    elif lookup:
        params["joined_lookup"] = lookup
    return dict(row, TRANSFORM_PARAMS={}, REPRESENTATION="catalog-resources",
                REPRESENTATION_PARAMS=params, APPROVAL_STATUS="APPROVED", LINEAGE_REQUIRED_FLAG=False)


def _compile_native_catalog_mapping(row):
    target = row["FIELD_RELATIVE_PATH"]
    transform = row["TRANSFORM_ID"]
    extra_property = target == "props" and transform in {"json-value", "timestamp", "catalog-record-reference"}
    required = (_registry_meta_bool(row, "VALUE_REQUIRED")
                if row.get("VALUE_REQUIRED") not in (None, "") else False)
    expected = {
        "": "reference-ids", "id": "oscal-token",
        "title": "text", "parts": "prose-direct",
        "props": "archer-guid-procedure-props",
    }
    if (row["EXECUTION_STATUS"] != "APPROVED" or (expected.get(target) != transform and not extra_property)
            or (row.get("VALUE_SOURCE") or "FIELD") != "FIELD"
            or (row.get("NULL_POLICY") or "omit") != "omit"
            or _lineage_required(row)
            or required != (target in {"id", "title"})):
        raise ValueError("Native Catalog mapping field/transform/required contract invalid")
    if any(row.get(k) not in (None, "") for k in (
            "ALLOWED_VALUES", "VALUE_MAP", "OTHER_REMARKS_TEMPLATE", "ROLE_ID",
            "ROLE_TITLE", "REFERENCE_TYPE", "DESCRIPTION_REQUIRED")):
        raise ValueError("Unsupported native Catalog mapping option")
    name = row.get("PROPERTY_NAME")
    namespace = None
    if extra_property:
        name = _metadata_column_text(row, "PROPERTY_NAME", True)
        namespace = _metadata_column_text(row, "PROPERTY_NAMESPACE", True)
        if name == "archer-content-id" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise ValueError("Native Catalog property name is reserved or invalid")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+", namespace):
            raise ValueError("Native Catalog property namespace must be an absolute URI")
    elif target == "parts":
        if name not in {"statement", "guidance"}:
            raise ValueError("Native Catalog part PROPERTY_NAME must be statement or guidance")
        namespace = row.get("PROPERTY_NAMESPACE") or None
        if name == "guidance" and namespace:
            raise ValueError("Native Catalog guidance does not use a namespace")
        if name == "statement" and namespace not in (None, "urn:archer:source:v1"):
            raise ValueError("Native Catalog optional statement parts require the Archer source namespace")
        if (name == "guidance" or namespace) and not re.fullmatch(r"[A-Z][A-Z0-9_]*", row["SOURCE_FIELD_NAME"] or ""):
            raise ValueError("Native Catalog optional parts require an exact source field")
    elif name not in (None, ""):
        raise ValueError("Native Catalog mapping has an unexpected PROPERTY_NAME")
    representation = {
        "native_control_lookup": _metadata_column_text(row, "LOOKUP_KEY", True),
        "target": target,
        "required": required,
    }
    if name:
        representation["property_name"] = name
    if namespace:
        representation["property_namespace"] = namespace
    return dict(row, TRANSFORM_PARAMS={}, REPRESENTATION="catalog-controls",
                REPRESENTATION_PARAMS=representation, APPROVAL_STATUS="APPROVED",
                LINEAGE_REQUIRED_FLAG=False)


def _compile_mapping(row, elements):
    """Translate explicit CSV columns to the parameters used by Cell 4."""
    transform = _metadata_column_text(row, "TRANSFORM_ID", True)
    if transform not in METADATA_TRANSFORM_IDS:
        raise ValueError("Unknown reusable TRANSFORM_ID: " + str(transform))
    if transform in {"archer-guid-procedure-props", "catalog-owner-procedure-props"} and row.get("PROPERTY_NAMESPACE") not in (None, ""):
        raise ValueError("GUID-derived namespaces cannot be overridden by PROPERTY_NAMESPACE")
    if row["EXECUTION_STATUS"] == "BLOCKED_IF_POPULATED" and transform != "reject-populated":
        raise ValueError("Populated-only guard requires reject-populated")
    operator = elements[row["OWNER_ELEMENT_PATH"]]["operator"]
    target = row["FIELD_RELATIVE_PATH"]
    if operator == "record" and row.get("LOOKUP_KEY"):
        bindings = elements[row["OWNER_ELEMENT_PATH"]]["parameters"].get("record_joined_bindings", {})
        if (row["LOOKUP_KEY"] not in bindings or transform != "text" or not target
                or (row.get("VALUE_SOURCE") or "FIELD") != "FIELD"
                or (row.get("NULL_POLICY") or "omit") != "omit"):
            raise ValueError("Appended record mappings require a declared forward lookup and text member")
        operator = "joined-records"
    if operator == "inline-links":
        if row.get("VALUE_REQUIRED") not in (None, "") and _registry_meta_bool(row, "VALUE_REQUIRED"):
            raise ValueError("Inline links VALUE_REQUIRED=true is unsupported")
        if (transform != "direct" or target or (row.get("VALUE_SOURCE") or "FIELD") != "FIELD"
                or _lineage_required(row) or any(row.get(k) not in (None, "") for k in
                    ("PROPERTY_NAME", "PROPERTY_NAMESPACE", "LOOKUP_KEY", "REFERENCE_TYPE"))):
            raise ValueError("Inline links require direct field collection projection without member overrides")
    if transform == "archer-guid-procedure-props" and operator != "catalog-controls":
        raise ValueError("Procedure GUID properties require an existing native Catalog Control")
    if transform == "catalog-record-reference" and operator != "catalog-controls":
        raise ValueError("Catalog record reference properties require an existing Catalog Control")
    if operator == "catalog-controls":
        return _compile_native_catalog_mapping(row)
    if transform == "catalog-source-links" and operator != "catalog-resources":
        raise ValueError("Native SOURCE_LINKS cannot target a different registry operator")
    if transform in {"resource-base64", "resource-citation"}:
        if operator != "catalog-resources":
            raise ValueError("Resource member transform requires the registered resource collection")
        return _compile_resource_member_mapping(row, elements)
    if operator == "catalog-resources":
        if (row["OWNER_ELEMENT_PATH"] != "catalog.back-matter.resources[]"
                or row["FIELD_RELATIVE_PATH"] or not row["SOURCE_FIELD_NAME"]
                or row["TRANSFORM_ID"] != "catalog-source-links"
                or row["EXECUTION_STATUS"] != "APPROVED"
                or (row.get("VALUE_SOURCE") or "FIELD") != "FIELD"
                or (row.get("NULL_POLICY") or "omit") != "omit"
                or _lineage_required(row)
                or any(row.get(name) not in (None, "") for name in (
                    "PROPERTY_NAME", "LOOKUP_KEY", "REFERENCE_TYPE", "VALUE_REQUIRED",
                    "ALLOWED_VALUES", "VALUE_MAP", "OTHER_REMARKS_TEMPLATE", "ROLE_ID",
                    "ROLE_TITLE", "DESCRIPTION_REQUIRED"))):
            raise ValueError("Back Matter SOURCE_LINKS mapping violates native resource contract")
        return dict(row, TRANSFORM_PARAMS={}, REPRESENTATION="catalog-resources",
                    REPRESENTATION_PARAMS={"source_field": row["SOURCE_FIELD_NAME"]},
                    APPROVAL_STATUS="APPROVED", LINEAGE_REQUIRED_FLAG=False)
    params, representation = {}, {}
    if target:
        if operator not in {"object", "record", "optional-record", "values", "named-parts", "joined-records"} or not re.fullmatch(r"[\w-]+(?:\.[\w-]+)*", target):
            raise ValueError("Member target conflicts with its element operator")
        representation["target"] = target
    source = row.get("VALUE_SOURCE") or "FIELD"
    if source not in {"FIELD", "CONFIG"} or source == "CONFIG" and (operator not in {"object", "record", "optional-record"} or not target):
        raise ValueError("CONFIG values require an explicit object member target")
    if source == "CONFIG":
        representation["value_source"] = source
    if transform == "json-value" and (source != "FIELD" or not (operator in {"properties", "observations"} or operator == "joined-records" and target == "props") or not row.get("PROPERTY_NAMESPACE")):
        raise ValueError("Typed JSON values require namespaced field properties")
    lineage_required = _lineage_required(row)
    if lineage_required and (source == "CONFIG" or transform in {"skip", "reject-populated"}):
        raise ValueError("LINEAGE_REQUIRED=Y requires an approved source FIELD mapping")
    if lineage_required and operator in {"properties", "observations"}:
        raise ValueError("LINEAGE_REQUIRED=Y is reserved for native members or responsible-party assignments")
    if lineage_required and operator not in {"assignments", "references"} and not target:
        raise ValueError("LINEAGE_REQUIRED=Y requires a native OSCAL member target, responsible-party assignment, or reference collection")
    null_policy = row.get("NULL_POLICY") or "omit"
    if null_policy not in {"omit", "preserve"}:
        raise ValueError("NULL_POLICY must be omit or preserve")
    if null_policy == "preserve":
        if source != "FIELD" or transform not in {"direct", "text", "archer-select", "scalar-score", "security-objective", "json-text"} or operator not in {"object", "record", "optional-record", "properties", "observations"}:
            raise ValueError("Null preservation requires a scalar member or property mapping")
        representation["preserve_null"] = True
    if row.get("VALUE_REQUIRED") not in (None, ""):
        representation["required"] = _registry_meta_bool(row, "VALUE_REQUIRED")
    if transform == "skip" and representation.get("required"):
        raise ValueError("Skip transform cannot supply a required value")
    if transform in {"oscal-token", "oscal-scoped-group-id"} and (
            operator != "joined-records" or target != "id" or not representation.get("required")):
        raise ValueError("OSCAL group identifier transform requires a required joined-record id")
    allowed = {"VALUE_SOURCE", "VALUE_REQUIRED"}
    if row.get("PROPERTY_NAMESPACE") not in (None, ""):
        if operator not in {"properties", "observations", "named-parts"} and not (operator == "joined-records" and target == "props"):
            raise ValueError("PROPERTY_NAMESPACE requires a property collection, joined-records, or named parts")
        namespace = _metadata_column_text(row, "PROPERTY_NAMESPACE", True)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+", namespace):
            raise ValueError("PROPERTY_NAMESPACE must be an absolute URI")
        allowed.add("PROPERTY_NAMESPACE")
        representation["property_namespace"] = namespace
    if operator == "joined-records":
        allowed.add("LOOKUP_KEY")
        representation["joined_lookup"] = _metadata_column_text(row, "LOOKUP_KEY", True)
    if row.get("PROPERTY_NAME") not in (None, ""):
        if operator not in {"properties", "observations", "named-parts"} and not (
                operator == "joined-records" and
                (target in {"props", "parts"} or
                 target == "id" and transform in {"oscal-token", "oscal-scoped-group-id"})):
            raise ValueError("PROPERTY_NAME requires a property collection or joined group property/part")
        allowed.add("PROPERTY_NAME")
        property_name = _metadata_column_text(row, "PROPERTY_NAME", True)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", property_name):
            raise ValueError("PROPERTY_NAME contains unsupported characters")
        representation["property_name"] = property_name
    if operator == "joined-records" and target in {"props", "parts"} and not representation.get("property_name"):
        raise ValueError("Joined-record embedded property or part requires an explicit PROPERTY_NAME")
    if transform == "catalog-owner-procedure-props":
        if not ((operator == "properties" and not target) or (operator == "joined-records" and target == "props")):
            raise ValueError("Owner Procedure properties require a properties collection or joined-record props target")
        if (source != "FIELD" or null_policy != "omit" or lineage_required
                or representation.get("required") or representation.get("property_name") != "procedure-reference"):
            raise ValueError("Owner Procedure properties require the reviewed reference encoding")
        representation["owner_procedure_binding"] = _owner_procedure_key(row["OWNER_ELEMENT_PATH"], row["SOURCE_FIELD_NAME"], representation.get("joined_lookup"))
    if transform == "catalog-related-subsections":
        if (operator != "joined-records" or row["OWNER_ELEMENT_PATH"] != "catalog.groups[].groups[].groups[]"
                or target != "links" or representation.get("joined_lookup") != "subsections"
                or row.get("REFERENCE_TYPE") != "related" or row.get("PROPERTY_NAME") not in (None, "")
                or source != "FIELD" or null_policy != "omit" or representation.get("required") or lineage_required):
            raise ValueError("Related Sub-Section link mapping requires the reviewed native contract")
        allowed.add("REFERENCE_TYPE")
        representation["link_rel"] = "related"
    if transform == "oscal-scoped-group-id" and not representation.get("property_name"):
        raise ValueError("Scoped native group ID requires a named original Archer ID property")
    if operator == "named-parts" and not (
            target == "prose" and source == "FIELD" and transform in {"prose-direct", "prose-or-link-array"}
            and representation.get("property_name") and not lineage_required):
        raise ValueError("Named parts require field prose-direct, prose target and explicit PROPERTY_NAME")
    if transform == "prose-or-link-array" and not (
            operator == "named-parts" and target == "prose" and source == "FIELD"
            and representation.get("property_namespace")):
        raise ValueError("prose-or-link-array requires namespaced field-based named-part prose")
    if transform == "prose-direct" and not (
            (operator == "joined-records" and target == "parts" or
             operator == "named-parts" and target == "prose")
            and representation.get("property_name")):
        raise ValueError("prose-direct requires named joined-record native parts")
    if transform == "status-crosswalk":
        allowed.update(("VALUE_MAP", "OTHER_REMARKS_TEMPLATE"))
        crosswalk = {}
        for entry in _metadata_items(row, "VALUE_MAP"):
            if entry.count("=") != 1:
                raise ValueError("VALUE_MAP entries must be source=target")
            src_label, tgt_label = (part.strip() for part in entry.split("=", 1))
            src_label = re.sub(r"[^a-z0-9]+", "-", src_label.lower()).strip("-")
            if not src_label or not tgt_label or src_label in crosswalk:
                raise ValueError("VALUE_MAP contains empty or conflicting labels")
            crosswalk[src_label] = tgt_label
        if not crosswalk:
            raise ValueError("Crosswalk requires VALUE_MAP")
        params["crosswalk"] = crosswalk
        template = row.get("OTHER_REMARKS_TEMPLATE")
        if template:
            if template.count("{label}") != 1 or any(c in template.replace("{label}", "") for c in "{}"):
                raise ValueError("OTHER_REMARKS_TEMPLATE requires one {label} placeholder")
            params["other_remarks_prefix"], params["other_remarks_suffix"] = template.split("{label}")
        elif "other" in crosswalk.values():
            raise ValueError("Crosswalk other value requires an explanation")
    if operator == "assignments":
        allowed.update(("ROLE_ID", "ROLE_TITLE"))
        representation.update(role_id=_metadata_column_text(row, "ROLE_ID", True),
                              role_title=_metadata_column_text(row, "ROLE_TITLE", True))
    if operator == "references":
        allowed.update(("REFERENCE_TYPE", "LOOKUP_KEY", "DESCRIPTION_REQUIRED"))
        representation["reference_type"] = _metadata_column_text(row, "REFERENCE_TYPE", required=bool(row.get("LOOKUP_KEY")))
        if row.get("LOOKUP_KEY"):
            representation["hydrate_lookup"] = _metadata_column_text(row, "LOOKUP_KEY")
        if row.get("DESCRIPTION_REQUIRED") not in (None, ""):
            if not row.get("LOOKUP_KEY"):
                raise ValueError("DESCRIPTION_REQUIRED needs LOOKUP_KEY")
            representation["description_required"] = _registry_meta_bool(row, "DESCRIPTION_REQUIRED")
    columns = {
        "ALLOWED_VALUES", "VALUE_MAP", "OTHER_REMARKS_TEMPLATE", "ROLE_ID", "ROLE_TITLE",
        "REFERENCE_TYPE", "LOOKUP_KEY", "DESCRIPTION_REQUIRED", "VALUE_SOURCE", "VALUE_REQUIRED",
        "PROPERTY_NAME",
    }
    if any(row.get(key) not in (None, "") for key in columns - allowed):
        raise ValueError("CSV parameter does not apply to the selected operation")
    return dict(row, TRANSFORM_PARAMS=params, REPRESENTATION=operator, REPRESENTATION_PARAMS=representation,
                APPROVAL_STATUS=row["EXECUTION_STATUS"], LINEAGE_REQUIRED_FLAG=lineage_required)


def _compile_scalar_array_contracts(selected, elements, route, model):
    declarations = route.get("scalar_array_properties", [])
    if not isinstance(declarations, list):raise ValueError("Scalar array declarations must be a list")
    indexed = {}
    for d in declarations:
        if not isinstance(d,dict) or type(d.get("enabled")) is not bool:raise ValueError("Scalar array declaration invalid")
        if not d["enabled"]:continue
        key = _scalar_array_property_key(d["source_field"],d["owner_path"])
        if key in indexed:raise ValueError("Duplicate scalar array declaration")
        indexed[key] = d
    result = {}
    for row in selected:
        key = _scalar_array_property_key(row["SOURCE_FIELD_NAME"], row["OWNER_ELEMENT_PATH"])
        if row["TRANSFORM_ID"] != "scalar-array" and key not in indexed:continue
        params = row["REPRESENTATION_PARAMS"]
        operator = elements[row["OWNER_ELEMENT_PATH"]]["operator"]
        if not (operator == "properties" and not _metadata_target(row) or operator == "joined-records" and _metadata_target(row) == "props") or not params.get("property_name"):
            raise ValueError("Scalar arrays require explicit named property targets")
        d = indexed.get(key, {"enabled":True,"source_field":row["SOURCE_FIELD_NAME"],"owner_path":row["OWNER_ELEMENT_PATH"],"joined_lookup":params.get("joined_lookup"),"property_name":params["property_name"],"value_shape":"strict-flat-scalar-array","value_encoding":"sorted-unique-scalar-text-membership"})
        if key not in indexed and params.get("property_namespace"):
            d["property_namespace"] = params["property_namespace"]
        if d.get("property_namespace") != params.get("property_namespace"):raise ValueError("Scalar array namespace contract mismatch")
        if any(d.get(k)!=v for k,v in {"source_field":row["SOURCE_FIELD_NAME"],"owner_path":row["OWNER_ELEMENT_PATH"],"joined_lookup":params.get("joined_lookup"),"property_name":params["property_name"],"value_shape":"strict-flat-scalar-array","value_encoding":"sorted-unique-scalar-text-membership"}.items()):raise ValueError("Scalar array contract mismatch")
        if key in result:raise ValueError("Duplicate scalar array mapping")
        params["scalar_array_property_key"] = key
        if row["TRANSFORM_ID"] == "scalar-array":
            row["TRANSFORM_ID"] = "direct"
            params["scalar_array_csv"] = True
        result[key] = copy.deepcopy(d)
    if set(indexed)-set(result):raise ValueError("Scalar array declaration has no selected mapping")
    return {"release":SCALAR_ARRAY_PROPERTY_RELEASE,"contracts":result} if result else None



def _owner_procedure_key(owner, field, lookup):
    return json.dumps([owner, field, lookup], separators=(",", ":"))


def _compile_owner_procedure_contracts(selected, elements, route, model):
    rows = [r for r in selected if r["TRANSFORM_ID"] == "catalog-owner-procedure-props"]
    declarations = route.get("owner_procedure_properties", {})
    if not isinstance(declarations, (dict, list)):raise ValueError("Owner Procedure declarations required")
    declarations = [item for value in declarations.values() for item in (value if isinstance(value,list) else [value])] if isinstance(declarations, dict) else declarations
    indexed = {}
    for d in declarations:
        if not isinstance(d, dict) or type(d.get("enabled")) is not bool:raise ValueError("Owner Procedure enabled must be boolean")
        if not d["enabled"]:continue
        key = _owner_procedure_key(d.get("owner_path"), d.get("source_field"), d.get("joined_lookup"))
        if key in indexed:raise ValueError("Duplicate owner/field/lookup declaration")
        indexed[key] = d
    result = {}
    for row in rows:
        params = row["REPRESENTATION_PARAMS"]
        key = _owner_procedure_key(row["OWNER_ELEMENT_PATH"], row["SOURCE_FIELD_NAME"], params.get("joined_lookup"))
        d = indexed.get(key)
        if d is None:
            domain = route.get("field_guid_domain")
            if not (isinstance(domain,dict) and domain.get("enabled") is True
                    and domain.get("metadata_binding") == "route-guid-domain"
                    and params.get("joined_lookup") == domain.get("joined_lookup")
                    and domain.get("owner_path") == row["OWNER_ELEMENT_PATH"]):
                candidates = [(k,v) for k,v in indexed.items() if v.get("owner_path") == row["OWNER_ELEMENT_PATH"] and v.get("joined_lookup") == params.get("joined_lookup")]
                if not candidates:raise ValueError("Exact owner metadata domain required")
                domain_fields = ("metadata_table","level_id_column","field_id_column","guid_column","source_field_column","level_id")
                domains = {json.dumps({k:v.get(k) for k in domain_fields},sort_keys=True) for _,v in candidates}
                if len(domains) != 1:raise ValueError("Owner metadata domains are ambiguous")
                # All candidates prove the same exact metadata table/projection/level.
                # Reuse its deterministic declared snapshot, never another owner's frame.
                binding, domain = min(candidates,key=lambda item:item[0])
                domain = dict(domain,metadata_binding=binding)
            d = {k:domain.get(k) for k in ("metadata_table","level_id_column","field_id_column","guid_column","source_field_column","level_id","metadata_binding")}
            d.update(enabled=True, source_field=row["SOURCE_FIELD_NAME"], owner_path=row["OWNER_ELEMENT_PATH"], joined_lookup=params.get("joined_lookup"), field_id=None, field_id_resolution="unique-level-source-field", namespace_mode="archer-field-guid-urn", property_name=params.get("property_name"), value_encoding="one-string-per-procedure-id")
        if key in result:raise ValueError("Duplicate owner/field/lookup mapping")
        if (type(d.get("level_id")) is not int or d["level_id"] <= 0
                or not (type(d.get("field_id")) is int and d["field_id"] > 0 or d.get("field_id") is None and isinstance(d.get("metadata_binding"),str) and d.get("field_id_resolution") == "unique-level-source-field")
                or d.get("namespace_mode") != "archer-field-guid-urn"
                or d.get("value_encoding") != "one-string-per-procedure-id"
                or d.get("property_name") != params.get("property_name")
                or row["FIELD_RELATIVE_PATH"] != ("props" if params.get("joined_lookup") else "")):
            raise ValueError("Owner Procedure exact GUID/member contract invalid")
        if not isinstance(d.get("metadata_table"), str) or not re.fullmatch(r"[A-Za-z0-9_$]+(?:\.[A-Za-z0-9_$]+){2}", d["metadata_table"]):raise ValueError("Owner GUID metadata table required")
        cols = [d.get(k) for k in ("level_id_column", "field_id_column", "guid_column", "source_field_column")]
        if any(not isinstance(v,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*",v) for v in cols) or len({v.upper() for v in cols}) != 4:raise ValueError("Owner GUID columns invalid")
        result[key] = copy.deepcopy(d)
    if set(indexed)-set(result):raise ValueError("Enabled owner declarations require exact selected mappings")
    return {"release": OWNER_PROCEDURE_PROPERTY_RELEASE, "contracts": result} if result else None



def _compile_native_catalog_guid_contract(rows, contracts, binding, route):
    """One disabled-by-default, explicit Standard-field property extension."""
    declarations = route.get("native_control_guid_properties", {})
    if not isinstance(declarations, dict):
        raise ValueError("Native control GUID property contracts must be a mapping")
    contract = declarations.get(binding)
    if not rows:
        if isinstance(contract, dict) and contract.get("enabled") is True:
            raise ValueError("Enabled GUID property contract needs every declared placement mapping")
        return None
    if not isinstance(contract, dict) or contract.get("enabled") is not True:
        raise ValueError("Procedure GUID property contract must be explicitly enabled")
    allowed = {"enabled", "source_field", "level_id", "field_id", "namespace_mode", "property_name",
               "metadata_table", "level_id_column", "field_id_column", "guid_column",
               "source_field_column", "value_encoding"}
    if set(contract) != allowed:
        raise ValueError("Procedure GUID property contract requires explicit metadata and encoding")
    if (type(contract["level_id"]) is not int or contract["level_id"] <= 0
            or type(contract["field_id"]) is not int or contract["field_id"] <= 0
            or not isinstance(contract["source_field"], str) or not contract["source_field"]
            or contract["value_encoding"] != "one-string-per-procedure-id"):
        raise ValueError("Procedure GUID pilot requires exact Standard field and reviewed encoding")
    if (binding not in contracts or len(rows) != len(contracts[binding]["owner_bindings"])
            or {r["OWNER_ELEMENT_PATH"] for r in rows}
               != {p + ".controls[]" for p in contracts[binding]["owner_bindings"]}
            or any(r["SOURCE_FIELD_NAME"] != contract["source_field"] for r in rows)):
        raise ValueError("Procedure GUID pilot needs one matching rule per control placement")
    if (contract["namespace_mode"] != "archer-field-guid-urn"
            or not isinstance(contract["property_name"], str) or not contract["property_name"]):
        raise ValueError("Approved Procedure property name and GUID-URN namespace mode required")
    if not isinstance(contract["metadata_table"], str) or not re.fullmatch(
            r"[A-Za-z0-9_$]+(?:\.[A-Za-z0-9_$]+){2}", contract["metadata_table"]):
        raise ValueError("Explicit field GUID metadata table is required")
    for key in ("level_id_column", "field_id_column", "guid_column", "source_field_column"):
        if not isinstance(contract[key], str) or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_$]*", contract[key]):
            raise ValueError("Explicit field GUID metadata columns are required")
    if len({contract[key].upper() for key in (
            "level_id_column", "field_id_column", "guid_column", "source_field_column")}) != 4:
        raise ValueError("Field GUID metadata columns must be distinct")
    return copy.deepcopy(contract)



def _compile_native_catalog_hierarchy_reference(declaration, route, result):
    keys = {"source_field", "field_id", "subsection_lookup", "section_lookup", "target_level_id"}
    if (not isinstance(declaration, dict) or set(declaration) != keys
            or any(not isinstance(declaration[key], str) or not declaration[key].strip()
                   or declaration[key].strip() != declaration[key]
                   for key in ("source_field", "subsection_lookup", "section_lookup"))
            or any(type(declaration[key]) is not int or declaration[key] <= 0
                   for key in ("field_id", "target_level_id"))):
        raise ValueError("Invalid native Catalog control hierarchy reference declaration")
    subsection_key, section_key = declaration["subsection_lookup"], declaration["section_lookup"]
    owners = result["owner_bindings"]
    joined = route.get("joined_lookups", {})
    subsection, section = joined.get(subsection_key), joined.get(section_key)
    if (owners.get("catalog.groups[].groups[].groups[]") != subsection_key
            or owners.get("catalog.groups[].groups[]") != section_key
            or subsection_key == section_key or not isinstance(subsection, dict) or not isinstance(section, dict)
            or subsection.get("parent_binding") != section_key or subsection.get("require_single_parent") is not True
            or not subsection.get("join_json_array_field") or not section.get("source_table")
            or not result.get("guid_props")):
        raise ValueError("Native Catalog control hierarchy requires the configured Subsection and Section owner lookups")
    matching = [prop["reference"] for prop in result.get("extra_props", ())
                if prop.get("transform") == "catalog-record-reference"
                and prop["source_field"] == declaration["source_field"]]
    if len(matching) != 1:
        raise ValueError("Native Catalog control hierarchy requires one mapped source reference field")
    targets = matching[0].get("targets", [matching[0]])
    target = next((entry for entry in targets if entry["target_level_id"] == declaration["target_level_id"]), None)
    section_targets = [entry for entry in targets if entry["target_level_id"] == declaration["target_level_id"] - 1]
    contracts = route["native_controls"]
    if (target is None or not subsection.get("source_table")
            or contracts[target["lookup_key"]]["source_table"] != subsection["source_table"]
            or len(section_targets) != 1
            or contracts[section_targets[0]["lookup_key"]]["source_table"] != section["source_table"]):
        raise ValueError("Native Catalog control hierarchy must use the configured Subsection and parent Section target tables")
    return dict(declaration)


def _compile_native_catalog_plan(selected, elements, route, model):
    native = [r for r in selected if r["REPRESENTATION"] == "catalog-controls"]
    if not native:
        return None
    if model != "CATALOG":
        raise ValueError("Native Catalog controls cannot run under another model")
    contracts = route.get("native_controls", {})
    bindings = {r["REPRESENTATION_PARAMS"]["native_control_lookup"] for r in native}
    if not bindings.issubset(contracts):
        raise ValueError("Native Catalog requires configured lookup bindings")
    if len(bindings) > 1:
        families = [_compile_native_catalog_plan(
            [r for r in native if r["REPRESENTATION_PARAMS"]["native_control_lookup"] == binding],
            elements, route, model) for binding in sorted(bindings)]
        def domain(family):
            contract = contracts[family["lookup"]]
            return (contract.get("source_table"), contract.get("content_id_column", "CONTENT_ID"),
                    contract.get("json_column", "CURATED_JSON"), contract.get("target_level_id"),
                    contract.get("order_candidates", []))
        def semantics(family):
            return ({k: v for k, v in family["fields"].items() if k},
                    family.get("declared_owner_bindings", family.get("owner_bindings")),
                    family["paths"], family.get("id_policy"), family.get("guid_props"),
                    family.get("extra_props"), family.get("extra_parts"),
                    family.get("control_hierarchy_reference"))
        if any(domain(f) != domain(families[0]) for f in families[1:]):
            raise ValueError("Native Catalog reference families require the same target domain")
        if any(semantics(f) != semantics(families[0]) for f in families[1:]):
            raise ValueError("Native Catalog reference families have incompatible hydration or ownership")
        identities = [(f["fields"][""], tuple(f.get("reference_owner_paths", f.get("owner_bindings", {}))))
                      for f in families]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate native Catalog reference family")
        return {"plan_capability": "native-catalog-reference-families-v1", "families": families}
    binding = next(iter(bindings))
    target_level_id = contracts[binding].get("target_level_id")
    if "target_level_id" in contracts[binding] and (type(target_level_id) is not int or target_level_id <= 0):
        raise ValueError("NATIVE_REFERENCE_TARGET_LEVEL_INVALID")
    owners = contracts[binding].get("owner_bindings", {})
    explicit = contracts[binding].get("reference_owner_paths")
    if explicit is None:
        if set(owners) != set(NATIVE_CATALOG_OWNER_PATHS) or owners.get("catalog") is not None:
            raise ValueError("Native Catalog owner lookup coverage invalid")
        reference_owners = list(owners)
    else:
        allowed = set(NATIVE_CATALOG_OWNER_PATHS)
        if (not isinstance(owners, dict) or not owners or not set(owners).issubset(allowed)
                or "catalog" not in owners or owners["catalog"] is not None
                or any(p != "catalog" and p.rsplit(".", 1)[0] not in owners for p in owners)
                or not isinstance(explicit, list) or not explicit
                or any(not isinstance(p, str) for p in explicit)
                or len(set(explicit)) != len(explicit) or not set(explicit).issubset(owners)):
            raise ValueError("Native Catalog selected hierarchy/reference owners invalid")
        reference_owners = explicit
    paths = {p + ".controls[]" for p in owners}
    if {r["OWNER_ELEMENT_PATH"] for r in native} != paths:
        raise ValueError("Native Catalog requires every selected control placement path")
    fields_by_path = []
    props_by_path = []
    parts_by_path = []
    for path in sorted(paths):
        spec = elements[path]
        params = spec["parameters"]
        if (spec["operator"] != "catalog-controls"
                or params.get("required_members") != ["id", "title"]
                or params.get("include_uuid")
                or params["registry_contract"]["parent_path"] != path.rsplit(".", 1)[0]):
            raise ValueError("Native control registry contract invalid")
        path_rows = [r for r in native if r["OWNER_ELEMENT_PATH"] == path]
        optional_parts = [r for r in path_rows if r["FIELD_RELATIVE_PATH"] == "parts"
                          and (r["REPRESENTATION_PARAMS"].get("property_name") == "guidance"
                               or r["REPRESENTATION_PARAMS"].get("property_namespace"))]
        rows = [r for r in path_rows if r["FIELD_RELATIVE_PATH"] != "props" and r not in optional_parts]
        if len(rows) != 4 or {r["FIELD_RELATIVE_PATH"] for r in rows} != {"", "id", "title", "parts"}:
            raise ValueError("Every control placement needs one reference/id/title/statement mapping")
        fields_by_path.append({r["FIELD_RELATIVE_PATH"]: r["SOURCE_FIELD_NAME"] for r in rows})
        props_by_path.append(sorted(
            (r["SOURCE_FIELD_NAME"], r["REPRESENTATION_PARAMS"]["property_name"],
             r["REPRESENTATION_PARAMS"]["property_namespace"], r["TRANSFORM_ID"])
            for r in path_rows if r["TRANSFORM_ID"] in {"json-value", "timestamp", "catalog-record-reference"}
        ))
        parts_by_path.append(sorted((r["SOURCE_FIELD_NAME"], r["REPRESENTATION_PARAMS"]["property_name"],
                                     r["REPRESENTATION_PARAMS"].get("property_namespace") or "")
                                    for r in optional_parts))
    if any(fields != fields_by_path[0] for fields in fields_by_path):
        raise ValueError("All placements must hydrate the same native control fields")
    if any(properties != props_by_path[0] for properties in props_by_path):
        raise ValueError("All placements must hydrate the same native control properties")
    if any(parts != parts_by_path[0] for parts in parts_by_path):
        raise ValueError("All placements must hydrate the same native control optional parts")
    result = {"lookup": binding, "fields": fields_by_path[0],
              "owner_bindings": dict(owners), "paths": sorted(paths),
              "reference_owner_paths": reference_owners}
    if parts_by_path[0]:
        parts = []
        for field, name, namespace in parts_by_path[0]:
            part = dict(source_field=field, part_name=name, part_class=field.lower().replace("_", "-"))
            if namespace:
                part["part_namespace"] = namespace
            parts.append(part)
        result["extra_parts"] = parts
    if props_by_path[0]:
        properties = props_by_path[0]
        sources_by_property = {}
        for field, name, namespace, transform in properties:
            sources_by_property.setdefault((name, namespace), []).append((field, transform))
        extra_props = []
        for field, name, namespace, transform in properties:
            sources = sources_by_property[name, namespace]
            declaration = dict(source_field=field, property_name=name, namespace=namespace)
            if transform == "timestamp":
                declaration["transform"] = transform
            if transform == "catalog-record-reference":
                binding_config = contracts[binding].get("reference_properties", {})
                reference = binding_config.get(field) if isinstance(binding_config, dict) else None
                targets = reference.get("targets") if isinstance(reference, dict) and set(reference) == {"targets"} else [reference]
                target_keys = {"lookup_key", "target_level_id", "target_module_id", "display_name_field"}
                if (not isinstance(targets, list) or not targets
                        or any(not isinstance(target, dict) or set(target) != target_keys
                               or not isinstance(target["lookup_key"], str)
                               or target["lookup_key"] not in contracts
                               or any(type(target[key]) is not int or target[key] <= 0
                                      for key in ("target_level_id", "target_module_id"))
                               or not isinstance(target["display_name_field"], str)
                               or not target["display_name_field"].strip()
                               for target in targets)
                        or len({target["target_level_id"] for target in targets}) != len(targets)):
                    raise ValueError("Catalog record reference property requires an explicit target binding")
                declaration["transform"] = transform
                declaration["reference"] = copy.deepcopy(reference)
            if len(sources) > 1:
                if (any(kind != "timestamp" for _, kind in sources)
                        or len({source for source, _ in sources}) != len(sources)):
                    raise ValueError("Duplicate native Catalog property name and namespace")
                if (not (field.startswith("_") or field[:1].isalpha())
                        or any(not (char.isalnum() or char in ".-_") for char in field[1:])):
                    raise ValueError("Native Catalog timestamp property class must be a valid OSCAL token")
                declaration["class"] = field
            extra_props.append(declaration)
        result["extra_props"] = extra_props
    guid_props = _compile_native_catalog_guid_contract(
        [r for r in native if r["TRANSFORM_ID"] == "archer-guid-procedure-props"],
        contracts, binding, route)
    if guid_props is not None:
        result["guid_props"] = guid_props
    if "control_hierarchy_reference" in contracts[binding]:
        result["control_hierarchy_reference"] = _compile_native_catalog_hierarchy_reference(
            contracts[binding]["control_hierarchy_reference"], route, result)
    if target_level_id is not None:
        result["target_level_id"] = target_level_id
    if explicit is not None:
        if contracts[binding].get("id_policy") not in {"preserve-valid-token-reject-invalid", "normalize-invalid-token-v1"}:
            raise ValueError("Explicit native hierarchy requires an approved identifier policy")
        result["plan_capability"] = "native-catalog-selected-owners-v1"
        result["declared_owner_bindings"] = result.pop("owner_bindings")
        result["id_policy"] = contracts[binding]["id_policy"]
    else:
        result.pop("reference_owner_paths", None)
    return result



def _forward_binding_order(rows_by_binding, contracts, elements):
    """Validate finite forward dependencies and keep unrelated binding order stable."""
    forward = {key for key in rows_by_binding if contracts.get(key, {}).get("projection")
               in ("forward-raw-physical-v1", "forward-raw-physical-v2")}
    dependencies = {}
    paths = {}
    for key in forward:
        owners = {row["OWNER_ELEMENT_PATH"] for row in rows_by_binding[key]}
        if len(owners) != 1:
            raise ValueError("Forward lookup requires one mapped owner path")
        paths[key] = next(iter(owners))
        parent = contracts[key].get("parent_binding")
        if "parent_binding" in contracts[key]:
            if not isinstance(parent, str) or not parent or parent not in forward:
                raise ValueError("Forward parent binding must name a mapped forward family")
            dependencies[key] = parent
    order, active, visited = [], set(), set()
    def visit(key):
        if key in active:
            raise ValueError("Forward lookup dependency cycle")
        if key in visited:
            return
        active.add(key)
        if key in dependencies:
            visit(dependencies[key])
        active.remove(key); visited.add(key); order.append(key)
    for key in sorted(rows_by_binding, key=lambda k: (
            rows_by_binding[k][0]["OWNER_ELEMENT_PATH"].count("."),
            rows_by_binding[k][0]["OWNER_ELEMENT_PATH"], k)):
        visit(key)
    for key, parent in dependencies.items():
        parent_path = elements[paths[key]]["parameters"]["registry_contract"]["parent_path"]
        if parent_path != paths[parent]:
            raise ValueError("Forward parent binding must own the direct registry parent collection")
        parent_contract = contracts[parent]
        if (parent_contract.get("projection") == "forward-raw-physical-v2"
                and len(parent_contract.get("targets", [])) != 1):
            raise ValueError("Forward chain parent requires one unambiguous target domain")
    return order


def _mapping_route(row, route, model, paths, inactive, aliases, roots, routing, source_keys, unreviewed):
    status = row.get("EXECUTION_STATUS")
    original = row.get("OSCAL_ELEMENT_PATH") or ""
    path = original
    label = _model_token(row.get("OSCAL_MODEL"))
    owner_model, label_model = roots.get(path.split(".", 1)[0]), aliases.get(label)
    source = row.get("SOURCE_KEY")
    reason, severity = None, "BLOCKED"
    if status not in {None, "", "APPROVED", "BLOCKED_IF_POPULATED", "DEFERRED", "EXCLUDED"}:
        reason = "INVALID_EXECUTION_STATUS"
    elif source and source not in source_keys:
        reason = "UNKNOWN_SOURCE_KEY"
    elif source and source != route["source_key"]:
        reason, severity = "OTHER_SOURCE", "EXCLUDED"
    elif status and not source:
        reason = "MISSING_SOURCE_KEY"
    elif status in {"DEFERRED", "EXCLUDED"}:
        reason, severity = "EXPLICIT_" + status, status
    elif label_model and owner_model and label_model != owner_model or (
            status and owner_model and roots.get(original.split(".", 1)[0]) not in {None, owner_model}):
        reason = "MODEL_PATH_CONFLICT"
    elif label in routing["labels"] or path in routing["paths"]:
        reason, severity = "PLACEHOLDER_MAPPING", "DEFERRED"
    elif owner_model and owner_model != model or owner_model is None and label_model and label_model != model:
        reason, severity = "OTHER_MODEL", "EXCLUDED"
    elif any(row.get(key) not in (None, "") for key in (
            "TRANSFORM_PARAMS", "REPRESENTATION_PARAMS", "REPRESENTATION", "VALUE_CONSTRAINTS", "APPROVAL_STATUS")):
        reason = "RETIRED_MAPPING_METADATA"
    elif not status:
        reason, severity = "MISSING_APPROVED_METADATA", "DEFERRED" if unreviewed == "DEFER" else "BLOCKED"
    elif not row.get("SOURCE_FIELD_NAME"):
        reason = "MISSING_SOURCE_FIELD"
    elif not path or owner_model is None:
        reason = "UNKNOWN_MODEL_OR_PATH"
    elif any(path == boundary or path.startswith(boundary + ".") for boundary in inactive):
        reason = "REGISTRY_PATH_NOT_EXECUTABLE"
    owner = _owner_for_path(path, paths)
    relative = path[len(owner):].removeprefix(".") if owner else ""
    if not reason and (owner is None or any(token in relative for token in ("[", "]", ".."))):
        reason = "UNREGISTERED_COLLECTION"
    if reason:
        return None, {"reason": reason, "severity": severity, "field": row.get("SOURCE_FIELD_NAME")}
    return dict(row, ARTIFACT_MODEL=row.get("OSCAL_MODEL"), CANONICAL_ELEMENT_PATH=path,
                OWNER_ELEMENT_PATH=owner, FIELD_RELATIVE_PATH=relative, OSCAL_MODEL=model,
                OSCAL_FIELD_NAME=row.get("OSCAL_FIELD_NAME") or (relative.split(".")[-1] if relative else None)), None


def route_alias_index(route):
    models={}
    for candidate in ROUTES.values():models.setdefault(candidate["model"],candidate)
    models[route["model"]]=route
    aliases,roots={},{}
    for model,declaration in models.items():
        root=declaration["root"]
        if root in roots and roots[root]!=model:raise ValueError("Model root ownership conflict")
        roots[root]=model
        for label in (model,*declaration.get("csv_model_aliases",())):
            token=_model_token(label)
            if token:aliases[token]=model
    for row in route["structure"]:
        model,root=_registry_model(row),_registry_path(row).split(".",1)[0]
        roots[root]=model
        for label in (model,root,row.get("OSCAL_MODEL"),row.get("MODEL_NAME")):
            token=_model_token(label)
            if token:aliases[token]=model
    return aliases,roots


def compile_route(route, mapping_rows, alias_index):
    model=route["model"]
    registry=[_meta_row(row) for row in route["structure"]]
    active=[row for row in registry if _registry_meta_bool(row,"IS_ACTIVE")]
    mappings=[_meta_row(row) for row in mapping_rows]
    aliases,roots=alias_index
    routing={"labels":{_model_token(v) for v in ('TBD','N/A - Calculated','Multiple - See Notes')},
             "paths":{'TBD','All Nulls','Multiple - See Notes'}}
    model_rows = [row for row in active if _registry_model(row) == model]
    paths = {_registry_path(row) for row in model_rows}
    inactive = {_registry_path(row) for row in registry if _registry_model(row) == model} - paths
    selected, issues = [], []
    for index, row in enumerate(mappings):
        canonical, issue = _mapping_route(
            row, route, model, paths, inactive, aliases, roots,
            routing, {route["source_key"]}, "DEFER"
        )
        if issue:
            issues.append(dict(issue, row=index))
        else:
            selected.append(canonical)
    selected.sort(key=lambda row: (row["OWNER_ELEMENT_PATH"], row["CANONICAL_ELEMENT_PATH"], row["SOURCE_FIELD_NAME"]))
    root, model_rows, elements, groups = _registry_elements(model_rows, selected, route, model, route.get("inline_links"))
    report = {}
    if report:
        observations = [path for path, spec in elements.items() if spec["operator"] == "observations"]
        if len(observations) == 1 and "TARGET_PATH" not in report:
            report["TARGET_PATH"] = observations[0]
    config=dict(CONFIG,**copy.deepcopy(route.get("constant_values",{})))
    config.update({key:route[field] for key,field in _ROUTE_BINDINGS.items()})
    config.update(PHYSICAL_PROFILE="BINARY16_UUID32",MODEL_KEY=model)
    plan, contract_error = None, None
    if not any(issue["severity"] == "BLOCKED" for issue in issues):
        try:
            selected = [_compile_mapping(row, elements) for row in selected]
            identities = [
                (row["OWNER_ELEMENT_PATH"], row["SOURCE_FIELD_NAME"], row["FIELD_RELATIVE_PATH"],
                  (_metadata_params(row).get("joined_lookup") or _metadata_params(row).get("native_control_lookup"))
                  if (row["REPRESENTATION"] in {"catalog-resources", "joined-records", "catalog-controls"}
                      or elements[row["OWNER_ELEMENT_PATH"]]["parameters"].get("record_joined_bindings")) else None,
                 row["TRANSFORM_ID"] == "catalog-record-reference")
                for row in selected
            ]
            if len(set(identities)) != len(selected):
                raise ValueError("Duplicate mapping field target")
            joined_rows = {}
            for row in selected:
                binding = _metadata_params(row).get("joined_lookup")
                if row["REPRESENTATION"] == "joined-records" and binding:
                    joined_rows.setdefault(binding, []).append(row)
            _forward_binding_order(joined_rows, route.get("joined_lookups", {}), elements)
            options = {
                key: value for key, value in route.items()
                if key in {"parse_decimal", "null_source_as_empty", "preserve_null_observations"}
            }
            native_catalog = _compile_native_catalog_plan(selected, elements, route, model)
            owner_procedure_props = _compile_owner_procedure_contracts(selected, elements, route, model)
            scalar_array_properties = _compile_scalar_array_contracts(selected, elements, route, model)
            fingerprint_input = {
                "mappings": selected,
                "native_catalog": native_catalog,
                "owner_procedure_props": owner_procedure_props,
                "scalar_array_properties": scalar_array_properties,
            }
            appended = {key: value for key, value in route.get("joined_lookups", {}).items()
                        if "append_to_record_path" in value}
            if appended:
                fingerprint_input["record_joined_bindings"] = appended
            chains = {key: value for key, value in route.get("joined_lookups", {}).items()
                      if value.get("projection") in ("forward-raw-physical-v1", "forward-raw-physical-v2")
                      and "parent_binding" in value}
            if chains:
                fingerprint_input["forward_chains"] = chains
            if route.get("property_identity", {}).get("stable_fields") or route.get("property_identity", {}).get("reconcile_fields"):
                fingerprint_input["property_identity_contract"] = {k:v for k,v in route['property_identity'].items() if k!='migrate_value_ids'}
            fingerprint = hashlib.sha256(
                json.dumps(fingerprint_input, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            plan = dict(
                version=3, release=LEAN_MAPPER_RELEASE, elements=elements, mappings=selected,
                reference_groups=groups, mapping_fingerprint=fingerprint,
                options=options, report=report, native_catalog=native_catalog,
            )
            if owner_procedure_props is not None:
                plan["owner_procedure_props"] = owner_procedure_props
            if scalar_array_properties is not None:
                plan["scalar_array_properties"] = scalar_array_properties
        except ValueError as error:
            contract_error = str(error)
            issues.append(dict(row=None, field=None, reason="METADATA_CONTRACT_ERROR", severity="BLOCKED", affected_rows=len(selected)))
            selected = []
    counts = Counter()
    reasons = Counter()
    for issue in issues:
        counts[issue["severity"]] += issue.get("affected_rows", 1)
        reasons[issue["reason"]] += issue.get("affected_rows", 1)
    route_report = dict(
        STATUS="BLOCKED" if counts["BLOCKED"] else "READY",
        INPUT_ROWS=len(mappings),
        SELECTED_ROWS=len(selected),
        EXCLUDED_ROWS=counts["EXCLUDED"],
        DEFERRED_ROWS=counts["DEFERRED"],
        BLOCKED_ROWS=counts["BLOCKED"],
        REASON_COUNTS=dict(reasons),
        SEVERITY_COUNTS=dict(counts),
        ROUTING_POLICY="registry-first-v1",
        ISSUE_EVENTS_TOTAL=len(issues),
        ISSUE_SAMPLE_LIMIT=25,
        ISSUE_SAMPLES_TRUNCATED=len(issues) > 25,
        ISSUES=sorted(issues, key=lambda issue: issue["severity"] != "BLOCKED")[:25],
    )
    if contract_error:
        route_report["CONTRACT_ERROR"] = contract_error
    by_path = {}
    for row in selected:
        by_path.setdefault(row["OWNER_ELEMENT_PATH"], []).append(row)
    return dict(source_key=route["source_key"],route=route,config=config,
                mapping_rows=selected,registry_rows=model_rows,mappings_by_path=by_path,
                compiled_plan=plan,routing_report=route_report)

MAPPING_CONTEXTS=[compile_route(ROUTES[key],MAPPING_INPUTS[key[0]],route_alias_index(ROUTES[key])) for key in SELECTED_ROUTES]
print("Mapping routes:",[(c["source_key"],c["config"]["OSCAL_MODEL"],c["routing_report"]["STATUS"]) for c in MAPPING_CONTEXTS])

