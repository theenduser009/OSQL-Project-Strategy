# %% Cell 4 - Reusable transforms and registry operators

def _metadata_json_text(value):
    """Serialize parsed JSON numbers exactly, including finite Decimal values."""
    active = set()

    def encode(item):
        item = _to_python(item)
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError("JSON number must be finite")
            # Decimal's finite spelling is a JSON numeric token, not a string.
            # Never convert through float: that loses precision and exponent range.
            return str(item)
        if isinstance(item, (dict, list, tuple)):
            identity = id(item)
            if identity in active:
                raise ValueError("JSON value contains a cycle")
            active.add(identity)
            try:
                if isinstance(item, dict):
                    if any(not isinstance(key, str) for key in item):
                        raise ValueError("JSON object keys must be strings")
                    return "{" + ",".join(json.dumps(key) + ":" + encode(item[key])
                                           for key in sorted(item)) + "}"
                return "[" + ",".join(encode(member) for member in item) + "]"
            finally:
                active.remove(identity)
        if item is None or isinstance(item, (str, bool, int, float)):
            return json.dumps(item, allow_nan=False, separators=(",", ":"))
        raise TypeError("Value is not a JSON type")

    return encode(value)


import copy
import datetime
import hashlib
import json
import math
import re
import uuid
import unicodedata
from urllib.parse import urlsplit
from decimal import Decimal

SKIP_VALUE = object()
ARCHER_SELECT_ID_CONTAINER_KEYS = {"valuelistid", "valuelistids", "valueslistid", "valueslistids"}
_INLINE_REFERENCE_TRANSFORMS = {
    "reference-ids", "resource-citation", "catalog-related-subsections", "catalog-owner-procedure-props",
}
_INLINE_REFERENCE_RESERVED_KEYS = {"CONTENTID", "LEVELID", "CONTENT_ID", "LEVEL_ID"}
_INLINE_REPORT_FIELDS = ("BUSINESS", "ENTITY")
_INLINE_REPORT_FIELD_PREFIX = "_OSCAL_RESOLVED_RECORD_REFERENCES.Fields."


def _to_python(value):
    if hasattr(value, "as_dict"):
        return value.as_dict(recursive=True)
    return value.as_list() if hasattr(value, "as_list") else value


def _has_value(value):
    return value not in (None, "", [], {})


def _inline_projection_member(item):
    """Recognize the producer's bounded member shape at reference consumers only."""
    if type(item) is not dict or "ContentId" not in item:
        return None
    identity_keys = {"ContentId", "LevelId"} if "LevelId" in item else {"ContentId"}
    extras = item.keys() - identity_keys
    if len(extras) != 1:
        return None
    key = next(iter(extras))
    if (type(key) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", key)
            or key in _INLINE_REFERENCE_RESERVED_KEYS or key.startswith("OSCAL_")):
        return None
    for name in identity_keys:
        identity = item[name]
        if type(identity) not in (int, Decimal) or not re.fullmatch(r"[1-9][0-9]*", str(identity)):
            return None
    display = item[key]
    if (type(display) not in (str, bool, int, float, Decimal, datetime.date, datetime.datetime)
            or isinstance(display, float) and not math.isfinite(display)
            or isinstance(display, Decimal) and not display.is_finite()
            or type(display) is datetime.datetime and display.tzinfo is not None
            or not str(display).strip() or len(str(display).encode("utf-8")) > 512):
        return None
    original = int(item["ContentId"])
    if "LevelId" in identity_keys:
        original = {"ContentId": original, "LevelId": int(item["LevelId"])}
    return original, key, display


def _restore_inline_reference_value(value, expected_key=None):
    def restore(member):
        projection = _inline_projection_member(member)
        if projection is not None and (expected_key is None or projection[1] == expected_key):
            return projection[0]
        return member

    return [restore(item) for item in value] if type(value) is list else restore(value)


def _inline_reference_report_value(source_obj, field, raw, config):
    """Provide the existing SSP selector value without adding a RAW sidecar."""
    if (config.get("SOURCE_KEY") != "source-one"
            or config.get("SOURCE_TABLE_NAME") != "ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW"):
        return raw
    if field in _INLINE_REPORT_FIELDS:
        return _restore_inline_reference_value(raw, expected_key=field)
    reference_field = field.removeprefix(_INLINE_REPORT_FIELD_PREFIX)
    if field == reference_field or reference_field not in _INLINE_REPORT_FIELDS:
        return raw
    original = source_obj.get(reference_field)
    members = original if type(original) is list else [original]
    references = []
    for member in members:
        projection = _inline_projection_member(member)
        if projection is None or projection[1] != reference_field or type(projection[2]) is not str:
            continue
        _, key, display = projection
        references.append({"ContentId": int(member["ContentId"]), "LookupStatus": "RESOLVED",
                           "ResolvedRecord": {key: display}})
    return {"References": references} if references else raw


def resolve_json_path(source_obj, field_path, default=None):
    """Read a literal source key first, then a dotted/slash path or list index."""
    if not field_path:
        return default
    if isinstance(source_obj, dict) and field_path in source_obj:
        return _to_python(source_obj[field_path])
    current = source_obj
    for token in filter(None, re.split(r"[./]", str(field_path))):
        current = _to_python(current)
        if isinstance(current, dict):
            current = current.get(token, current.get(token.upper(), default))
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return default
    return _to_python(current)


def _stable_property_name(field):
    return re.sub(r"[^a-z0-9]+", "-", field.lower()).strip("-")


def _deterministic_uuid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(map(str, parts))))


def _deterministic_hash(*parts):
    return hashlib.md5("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def _json_text(value):
    return json.dumps(value, sort_keys=True, default=str, allow_nan=False)


def _scalar_text(value, shape_error, value_error, allow_bool=False):
    value = _to_python(value)
    if value is None or isinstance(value, (dict, list)) or isinstance(value, bool) and not allow_bool:
        raise ValueError(shape_error)
    text = ("true" if value else "false") if isinstance(value, bool) else str(value).strip()
    if not text or text.lower() in {"nan", "inf", "+inf", "-inf"}:
        raise ValueError(value_error)
    return text


def _oscal_property_values(value):
    return [_scalar_text(item, "Property value must be scalar", "Property value must be finite and nonblank", True)
            for item in (value if isinstance(value, list) else [value])]


def _extract_reference_ids(value):
    value = _to_python(value)
    if isinstance(value, dict):
        for key in ("UserList", "ValuesListIds", "ValueListIds", "ContentId", "ContentIds", "Ids", "Value"):
            if key in value and _has_value(value[key]):
                return _extract_reference_ids(value[key])
        for key, item in value.items():
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) in ARCHER_SELECT_ID_CONTAINER_KEYS and _has_value(item):
                return _extract_reference_ids(item)
    if isinstance(value, list):
        result = []
        for item in value:
            extracted = _extract_reference_ids(item)
            result.extend(extracted if isinstance(extracted, list) else [extracted])
        return result
    return value


def _contains_archer_select_id_container(value):
    value = _to_python(value)
    if isinstance(value, dict):
        return any(re.sub(r"[^a-z0-9]", "", str(key).lower()) in ARCHER_SELECT_ID_CONTAINER_KEYS
                   or _contains_archer_select_id_container(item) for key, item in value.items())
    return isinstance(value, list) and any(_contains_archer_select_id_container(item) for item in value)


def _resolved_select_labels(value):
    """Read Matillion-resolved select labels and prove they match source IDs."""
    value = _to_python(value)
    if not isinstance(value, dict):
        return None
    if "ResolvedValues" not in value:
        if _contains_archer_select_id_container(value):
            raise ValueError("Curated select field is missing ResolvedValues")
        return None
    resolved = _to_python(value.get("ResolvedValues"))
    if not isinstance(resolved, list):
        raise ValueError("ResolvedValues must be an array")

    source_ids = None
    for key in ("ValuesListIds", "ValueListIds"):
        if key in value and _has_value(value[key]):
            raw = _to_python(value[key])
            source_ids = raw if isinstance(raw, list) else [raw]
            break
    if source_ids is None:
        raise ValueError("ResolvedValues requires source value IDs")
    if len(resolved) != len(source_ids):
        raise ValueError("ResolvedValues cardinality does not match source value IDs")

    labels = []
    for source_id, item in zip(source_ids, resolved):
        item = _to_python(item)
        if not isinstance(item, dict):
            raise ValueError("ResolvedValues member must be an object")
        if item.get("LookupStatus") != "MATCHED":
            raise ValueError("ResolvedValues contains an unresolved value")
        resolved_id = item.get("ValueId")
        label = item.get("ValueName")
        if resolved_id is None or str(resolved_id).strip() != str(source_id).strip():
            raise ValueError("ResolvedValues identity does not match source value ID")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("ResolvedValues matched label must be nonblank text")
        labels.append(label.strip())
    return labels


def resolve_curated_select_value(value):
    """Return Matillion-resolved select labels; never query Archer metadata here."""
    resolved = _resolved_select_labels(value)
    if resolved is not None:
        return resolved
    if _contains_archer_select_id_container(value):
        raise ValueError("Curated select field is unresolved")
    return _to_python(value)


def resolve_archer_select_value(value, context=None):
    """Compatibility wrapper; production resolution is already in CURATED_JSON."""
    return resolve_curated_select_value(value)


def _single_curated_label(value):
    resolved = resolve_curated_select_value(value)
    values = resolved if isinstance(resolved, list) else [resolved]
    values = [item for item in values if item is not None]
    if len(values) != 1 or isinstance(values[0], (dict, list, bool)):
        return None
    label = str(values[0]).strip()
    return label or None


def normalize_security_objective(value):
    """Normalize already-resolved OSCAL CIA labels; no Archer lookup occurs here."""
    label = _single_curated_label(value)
    if label is None:
        return None
    candidate = label.lower()
    return candidate if candidate in {"low", "moderate", "high"} else None


def transform_fips_199(value, context=None):
    """Compatibility wrapper around OSCAL CIA normalization."""
    return normalize_security_objective(value)

def transform_document_identifier(value):
    return _scalar_text(value, "Document identifier must be scalar", "Document identifier must be finite and nonblank")


def transform_authorization_date(value):
    """Keep the source calendar date; never reinterpret an offset as UTC."""
    value = _to_python(value)
    if not _has_value(value):
        return SKIP_VALUE
    try:
        if isinstance(value, (datetime.datetime, datetime.date)):
            return datetime.date(value.year, value.month, value.day).isoformat()
        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
                return datetime.date.fromisoformat(text).isoformat()
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9]{2}:[0-9]{2}:[0-9]{2}"
                            r"(?:\.[0-9]{1,9})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?", text):
                text = text[:10] + "T" + text[11:]
                if text[-1:] in {"Z", "z"}:
                    text = text[:-1] + "+00:00"
                return datetime.datetime.fromisoformat(text).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        pass
    raise ValueError("Mapped date requires a valid ISO date or timestamp")


def _score_value(value, context):
    if not _has_value(value):
        return None
    if _contains_archer_select_id_container(value):
        value = resolve_curated_select_value(value)
    values = value if isinstance(value, list) else [value]
    if len(values) != 1 or not isinstance(values[0], (str, int, float, bool, Decimal)):
        raise ValueError("One scalar score is required per observation")
    item = values[0]
    if isinstance(item, float) and not math.isfinite(item) or isinstance(item, Decimal) and not item.is_finite():
        raise ValueError("Score must be finite")
    result = _oscal_property_values(item)[0]
    if result.lower() in {"infinity", "+infinity", "-infinity"}:
        raise ValueError("Score must be finite")
    return result


def _metadata_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be nonblank text")
    return value


def _is_oscal_token(value):
    """Use the same OSCAL token alphabet for normalization and control checks."""
    return (isinstance(value, str) and bool(value)
            and (value[0] == "_" or unicodedata.category(value[0]).startswith("L"))
            and all(ch in ".-_" or unicodedata.category(ch)[0] in {"L", "N"}
                    for ch in value[1:]))


def _oscal_token(value):
    """Convert only lexically invalid identifiers; retain valid Unicode tokens."""
    original = _to_python(value)
    if not isinstance(original, str) or not original.strip():
        raise ValueError("OSCAL token source must be nonblank text")
    if _is_oscal_token(original):
        return original
    pieces, last_dash = [], False
    for ch in original:
        if ch in ".-_" or unicodedata.category(ch)[0] in {"L", "N"}:
            pieces.append(ch)
            last_dash = False
        elif not last_dash:
            pieces.append("-")
            last_dash = True
    token = "".join(pieces).strip("-._")
    if not token:
        raise ValueError("OSCAL token has no permitted identifier characters")
    if not (token[0] == "_" or unicodedata.category(token[0]).startswith("L")):
        token = "g-" + token
    if not _is_oscal_token(token):
        raise ValueError("OSCAL token lexical validation failed")
    return token

def _scalar_array_property_contract(row, context):
    """Resolve only the exact compiled field/owner/property opt-in."""
    spec = context["compiled_plan"].get("scalar_array_properties")
    key = _metadata_params(row).get("scalar_array_property_key")
    if (not isinstance(spec,dict) or spec.get("release")!="catalog-owner-scalar-array-props-review-v1"
            or not isinstance(spec.get("contracts"),dict)):
        raise ValueError("Compiled scalar-array property contract is required")
    declared = context["route"].get("scalar_array_properties", [])
    expected = {item["owner_path"] + "|" + item["source_field"]: item for item in declared}
    for declared_key, declaration in expected.items():
        if spec["contracts"].get(declared_key) != declaration:
            raise ValueError("Compiled scalar-array contract differs from declared metadata")
    if key not in expected and not _metadata_params(row).get("scalar_array_csv"):
        raise ValueError("Scalar-array CSV opt-in required")
    contract = spec["contracts"].get(key)
    if (not isinstance(contract,dict) or contract.get("enabled") is not True
            or row["TRANSFORM_ID"]!="direct" or row["SOURCE_FIELD_NAME"]!=contract.get("source_field")
            or row["OWNER_ELEMENT_PATH"]!=contract.get("owner_path")
            or _metadata_params(row).get("joined_lookup")!=contract.get("joined_lookup")
            or _metadata_params(row).get("property_namespace")!=contract.get("property_namespace")
            or _metadata_params(row).get("property_name")!=contract.get("property_name")
            or key!=row["OWNER_ELEMENT_PATH"]+"|"+row["SOURCE_FIELD_NAME"]
            or contract.get("value_shape")!="strict-flat-scalar-array"
            or contract.get("value_encoding")!="sorted-unique-scalar-text-membership"):
        raise ValueError("Scalar-array property field/owner contract drift")
    return contract

def _scalar_array_property_membership(row, value, context):
    """Preserve finite flat scalar membership, without ID or ordering semantics."""
    _scalar_array_property_contract(row,context)
    value = _to_python(value)
    if value is None or isinstance(value,list) and not value:
        return SKIP_VALUE
    if not isinstance(value,list):
        raise ValueError("Scalar-array property source must be a JSON array")
    members = set()
    for raw in value:
        item = _to_python(raw)
        if type(item) not in (str,int,float,Decimal):
            raise ValueError("Scalar-array property members must be nonnull scalar values")
        if (isinstance(item,float) and not math.isfinite(item)
                or isinstance(item,Decimal) and not item.is_finite()):
            raise ValueError("Scalar-array numeric property members must be finite")
        text = _scalar_text(item,"Scalar-array property member must be scalar",
                            "Scalar-array property member must be finite and nonblank")
        if text.lower() in {"infinity","+infinity","-infinity"}:
            raise ValueError("Scalar-array property member must be finite")
        members.add(text)
    return sorted(members)

def _scalar_array_joined_legacy_props(props, path, context):
    """Validate only enabled repeated-name families; return every legacy prop."""
    spec = context["compiled_plan"].get("scalar_array_properties")
    if spec is None:
        return props
    if (not isinstance(spec,dict) or spec.get("release")!="catalog-owner-scalar-array-props-review-v1"
            or not isinstance(spec.get("contracts"),dict)):
        raise ValueError("Compiled scalar-array property contract is required")
    contracts = [contract for contract in spec["contracts"].values()
                 if contract.get("owner_path")==path and contract.get("enabled") is True]
    names = {(contract["property_name"],contract.get("property_namespace")) for contract in contracts}
    if len(names) != len(contracts):raise ValueError("Scalar-array property namespaces collide")
    if not names:
        return props
    legacy, seen = [],set()
    for prop in props:
        token = (prop.get("name"),prop.get("ns"))
        if token not in names:
            legacy.append(prop)
            continue
        expected_keys = {"name","value","ns"} if token[1] is not None else {"name","value"}
        if (set(prop)!=expected_keys or not isinstance(prop["value"],str)
                or not prop["value"] or prop["value"]!=prop["value"].strip()
                or (token,prop["value"]) in seen):
            raise ValueError("Invalid or duplicate opted-in scalar-array property")
        seen.add((token,prop["value"]))
    return legacy


def _metadata_transform(row, value, context):
    transform, params = row["TRANSFORM_ID"], row.get("TRANSFORM_PARAMS") or {}
    if transform == "prose-or-link-array":
        value = _to_python(value)
        if value == "":
            return SKIP_VALUE
        if isinstance(value, str):
            return _metadata_text(value, "Mapped prose")
        return _link_array_markup(value)
    if transform == "json-value":
        return _metadata_json_text(value)
    if _metadata_params(row).get("scalar_array_property_key"):
        return _scalar_array_property_membership(row,value,context)
    if transform == "catalog-owner-procedure-props":
        value = _to_python(value)
        if value is None or value == []:
            return SKIP_VALUE
        _procedure_ids(value)  # Fail before generic empty-object/string omission.
        return value
    if transform == "resource-base64":
        import base64
        import binascii
        value = _to_python(value)
        if value is None or value == "":
            return SKIP_VALUE
        if type(value) is not str or not value.isascii():
            raise ValueError("Embedded resource requires canonical base64 text")
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("Embedded resource requires canonical base64 text") from None
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("Embedded resource requires canonical base64 padding and pad bits")
        return {"value": value}
    if transform == "resource-citation":
        value = _to_python(value)
        if value is None or value == []:
            return SKIP_VALUE
        if type(value) is not list:
            raise ValueError("Resource citation references require an array")
        level = _metadata_params(row)["reference_level"]
        seen, result = set(), []
        for item in value:
            item = _to_python(item)
            if (type(item) is not dict or set(item) != {"ContentId", "LevelId"}
                    or type(item["ContentId"]) is not int or item["ContentId"] <= 0
                    or type(item["LevelId"]) is not int or item["LevelId"] != level):
                raise ValueError("Resource citation requires exact positive ContentId and declared LevelId")
            identity = str(item["ContentId"])
            if identity in seen:
                raise ValueError("Resource citation has duplicate reference identities")
            seen.add(identity)
            result.append(identity)
        return result
    if transform == "skip" or not _has_value(value):
        return SKIP_VALUE
    if transform == "catalog-source-links":
        value = _to_python(value)
        if not isinstance(value, list):
            raise ValueError("SOURCE_LINKS requires an array of link objects")
        return value
    if transform == "direct":
        return _to_python(value)
    if transform in {"text", "timestamp", "canonical-text", "prose-direct"}:
        value = _metadata_text(_to_python(value), "Mapped value")
        if transform == "canonical-text" and value != value.strip():
            raise ValueError("Controlled value must be canonical text")
        return value
    if transform == "date":
        return transform_authorization_date(value)
    if transform == "identifier":
        return transform_document_identifier(value)
    if transform in {"oscal-token", "oscal-scoped-group-id"}:
        return _oscal_token(value)
    if transform == "archer-select":
        result = resolve_curated_select_value(value)
        return result if _has_value(result) else SKIP_VALUE
    if transform == "reference-ids":
        result = _extract_reference_ids(value)
        return result if _has_value(result) else SKIP_VALUE
    if transform == "catalog-related-subsections":
        # Reference identity is validated again against SAME-Catalog children
        # at assembly time. Never synthesize a link to an unknown ContentId.
        items = _to_python(value)
        if not isinstance(items, list):
            raise ValueError("Related Sub-Section references must be a JSON array")
        identifiers = set()
        for item in items:
            item = _to_python(item)
            if isinstance(item, dict):
                if set(item) != {"ContentId", "LevelId"} or type(item["LevelId"]) is not int or item["LevelId"] != 9:
                    raise ValueError("Related Sub-Section item requires exact ContentId and LevelId 9")
                item = item["ContentId"]
            if type(item) is not int or item <= 0:
                raise ValueError("Related Sub-Section reference must be a positive integer ContentId")
            identifiers.add(str(item))
        return sorted(identifiers, key=int) if identifiers else SKIP_VALUE
    if transform == "json-text":
        try:
            return json.dumps(_to_python(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            raise ValueError("Mapped JSON text value is not serializable") from None
    if transform == "scalar-score":
        return _score_value(value, context)
    if transform == "security-objective":
        label = _single_curated_label(value)
        if label is None:
            raise ValueError("Security objective requires exactly one resolved Archer meta label")
        candidate = label.lower()
        return candidate if candidate in {"low", "moderate", "high"} else label
    if transform == "status-crosswalk":
        label = _single_curated_label(value)
        if label is None:
            raise ValueError("Crosswalk source label is unresolved or multivalued")
        target = params["crosswalk"].get(_stable_property_name(label))
        if target is None:
            raise ValueError("Label is absent from reviewed crosswalk")
        result = {"state": target}
        if target == "other":
            result["remarks"] = params["other_remarks_prefix"] + label + params.get("other_remarks_suffix", ".")
        return result
    raise ValueError("Populated source has no reviewed transformation")


def _metadata_mapped_value(row, source_obj, context):
    field, params = row["SOURCE_FIELD_NAME"], _metadata_params(row)
    raw = (context["config"].get(field) if params.get("value_source") == "CONFIG"
           else resolve_json_path(source_obj, field, default=SKIP_VALUE))
    try:
        if params.get("value_source") != "CONFIG":
            raw = _inline_reference_report_value(source_obj, field, raw, context["config"])
            forward_reference = not params.get("joined_lookup") and any(
                item.get("projection") in ("forward-raw-physical-v1", "forward-raw-physical-v2")
                and item.get("reference_field") == field
                for item in context.get("route", {}).get("joined_lookups", {}).values()
            )
            if (row["TRANSFORM_ID"] in _INLINE_REFERENCE_TRANSFORMS or params.get("scalar_array_property_key")
                    or row.get("REPRESENTATION") == "references" or forward_reference):
                raw = _restore_inline_reference_value(raw)
        if raw is SKIP_VALUE:
            value = SKIP_VALUE
        elif (raw is None and (params.get("preserve_null") or (
              row["TRANSFORM_ID"] == "scalar-score" and row["REPRESENTATION"] == "observations"
              and context["compiled_plan"]["options"].get("preserve_null_observations", False)))):
            value = None
        else:
            value = _metadata_transform(row, raw, context)
        if params.get("required") and (value is SKIP_VALUE or not _has_value(value)):
            raise ValueError("Required mapped value is absent after conversion")
    except (TypeError, ValueError, ArithmeticError):
        context["graph_report"]["STATUS"] = "BLOCKED"
        raise ValueError("Mapping failed for field " + field) from None
    context["graph_report"]["MISSING_VALUES" if value is SKIP_VALUE else "MAPPED_VALUES"] += 1
    return value


def _oscal_prop(name, value):
    """Build one small OSCAL property."""
    prop = {"name": _metadata_text(name, "Property name"), "value": value}
    if value is not None and not isinstance(value, str):
        raise ValueError("Property value must be text or an explicitly preserved warehouse null")
    return prop

def _capture_contribution(contributions, row, target, context, origin=None):
    expected_target = _metadata_target(row)
    reference_root = (
        row.get("REPRESENTATION") == "references"
        and expected_target is None
        and target == ""
    )
    if row.get("LINEAGE_REQUIRED_FLAG") and (target == expected_target or reference_root):
        contribution = {"source_field": row["SOURCE_FIELD_NAME"], "target": target, "origin": origin}
        if contribution not in contributions:
            contributions.append(contribution)

def _assign_mapped(payload, row, target, value, contributions, context, origin=None,
                   preserve_existing=False, null_coalesce=False):
    assigned = _metadata_assign(payload, target, value, preserve_existing, null_coalesce)
    # A present, explicitly preserved CIA null still has an Archer source-field
    # identity. Record its lineage even if a populated sibling won the target.
    # Missing source keys are skipped earlier in _metadata_instances.
    if assigned or (null_coalesce and value is None
                    and _metadata_params(row).get("preserve_null")):
        _capture_contribution(contributions, row, target, context, origin)


def _metadata_assign(payload, target, value, preserve_existing=False, null_coalesce=False):
    current, tokens = payload, target.split(".")
    for token in tokens[:-1]:
        current = current.setdefault(token, {})
        if not isinstance(current, dict):
            raise ValueError("Nested payload member conflicts with scalar")
    member = tokens[-1]
    if member in current and _json_text(current[member]) != _json_text(value):
        if null_coalesce:
            if value is None:
                return False
            if current[member] is None:
                current[member] = copy.deepcopy(value)
                return True
        if preserve_existing:
            return False
        raise ValueError("Singleton target has conflicting populated mappings")
    current[member] = copy.deepcopy(value)
    return True


def _metadata_get(payload, target):
    current = payload
    for token in target.split("."):
        current = current.get(token) if isinstance(current, dict) else None
    return current


def _metadata_parent_key(parameters, source_record_id):
    rule = parameters.get("parent_instance_rule")
    if rule == "source-record":
        return source_record_id
    return "singleton" if rule == "singleton" else None


def _append_unique_collection_instance(instances, instance):
    for existing in instances:
        if existing["instance_key"] == instance["instance_key"]:
            if _json_text(existing["payload"]) != _json_text(instance["payload"]):
                raise ValueError("Collection identity resolves to conflicting payloads")
            for contribution in instance.get("contributions", ()):
                if contribution not in existing.setdefault("contributions", []):
                    existing["contributions"].append(contribution)
            return
    instances.append(instance)


def _party_reference_identifier(item):
    item = _to_python(item)
    if isinstance(item, dict):
        item = item.get("Id") or item.get("UserId") or item.get("ContentId")
        if not _has_value(item):
            raise ValueError("Responsible-party reference has no stable identifier")
        return str(item).strip()
    return _scalar_text(item, "Responsible-party reference identifier is invalid", "Responsible-party reference identifier is empty")


def _party_resolved_user(item):
    item = _to_python(item)
    if not isinstance(item, dict) or "ResolvedUser" not in item:
        return None
    resolved = _to_python(item.get("ResolvedUser"))
    if not isinstance(resolved, dict):
        raise ValueError("ResolvedUser must be an object")
    if resolved.get("ContractVersion") != "archer-meta-user-v1":
        raise ValueError("ResolvedUser contract version is unsupported")
    status = resolved.get("LookupStatus")
    if status not in {"MATCHED", "MATCHED_MISSING_EEID", "USER_NOT_FOUND"}:
        raise ValueError("ResolvedUser lookup status is unsupported")
    return resolved


def _party_resolved_text(resolved, name):
    value = resolved.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("ResolvedUser " + name + " must be text")
    value = value.strip()
    return value or None


def _party_payload(item, party_uuid, party_type, context):
    payload = {"uuid": party_uuid, "type": party_type}
    resolved = _party_resolved_user(item)
    if resolved is None or resolved["LookupStatus"] == "USER_NOT_FOUND":
        return payload

    name_parts = [
        value for name in ("FIRST_NAME", "MIDDLE_NAME", "LAST_NAME")
        if (value := _party_resolved_text(resolved, name)) is not None
    ]
    if name_parts:
        payload["name"] = " ".join(name_parts)

    eeid = _party_resolved_text(resolved, "EEID")
    if resolved["LookupStatus"] == "MATCHED" and eeid is None:
        raise ValueError("ResolvedUser MATCHED record is missing EEID")

    scheme = context["config"].get("ARCHER_EEID_SCHEME")
    if eeid is not None and scheme is not None:
        if not isinstance(scheme, str) or not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", scheme.strip()):
            raise ValueError("ARCHER_EEID_SCHEME must be an absolute URI")
        payload["external-ids"] = [{"scheme": scheme.strip(), "id": eeid}]
    return payload


def _merge_party_payload(existing, candidate):
    if existing["uuid"] != candidate["uuid"] or existing["type"] != candidate["type"]:
        raise ValueError("Party identity resolves to conflicting core payload")
    merged = copy.deepcopy(existing)
    for member in ("name", "external-ids"):
        if member not in candidate:
            continue
        if member in merged and _json_text(merged[member]) != _json_text(candidate[member]):
            raise ValueError("Party identity resolves to conflicting enriched payload")
        merged[member] = copy.deepcopy(candidate[member])
    return merged


def _component_reference_content_ids(value):
    result = []
    for item in (value if isinstance(value, list) else [value]):
        item = _to_python(item)
        item = item.get("ContentId") if isinstance(item, dict) else item
        result.append(_scalar_text(item, "Component reference has invalid ContentId", "Component reference has invalid ContentId"))
    return result


def _component_text(value, label, required):
    if value is None or isinstance(value, str) and not value.strip():
        if required:
            raise ValueError("Component hydration " + label + " is missing")
        return None
    if not isinstance(value, str):
        raise ValueError("Component hydration " + label + " must be text")
    return value.strip()


def _build_component_hydration_lookups(source_df, mapping_rows, source_dfs, context):
    """Stream frozen references once; fetch only needed lookup IDs in bounded SQL batches."""
    from snowflake.snowpark import functions as F
    contracts, fields = {}, {}
    for row in mapping_rows:
        params = _metadata_params(row)
        kind, binding = params["reference_type"], params.get("hydrate_lookup")
        if not binding:
            continue
        contract = dict(context["lookups"]["component_contract"][binding], binding=binding,
                        description_required=bool(params.get("description_required")))
        if contracts.setdefault(kind, contract) != contract:
            raise ValueError("Reference type has contradictory hydration contracts")
        fields[row["SOURCE_FIELD_NAME"]] = kind
    if not fields:
        return {}
    ids, types = {kind: set() for kind in contracts}, {}
    for record in source_df.to_local_iterator():
        source = _metadata_parse(record, context)
        for field, kind in fields.items():
            value = resolve_json_path(source, field)
            if not _has_value(value):
                continue
            if not isinstance(value, list):
                raise ValueError("Approved component reference root must be an array")
            for identifier in _component_reference_content_ids(value):
                if types.setdefault(identifier, kind) != kind:
                    raise ValueError("Component hydration identity has a type collision")
                ids[kind].add(identifier)
    lookups = {}
    for kind, contract in contracts.items():
        frame = source_dfs[contract["binding"]]
        columns = {str(name).strip('"').upper(): name for name in frame.columns}
        identifier_col = F.trim(F.col(columns["CONTENT_ID"]).cast("string"))
        identifiers, found = sorted(ids[kind]), {}
        for start in range(0, len(identifiers), 1000):
            batch = frame.filter(identifier_col.isin(identifiers[start:start + 1000])).select(
                identifier_col.alias("CONTENT_ID"), F.col(columns["CURATED_JSON"]).alias("CURATED_JSON"))
            for record in batch.to_local_iterator():
                identifier = record["CONTENT_ID"]
                if identifier in found:
                    raise ValueError("Component lookup contains duplicate ContentId values")
                payload = _metadata_parse(record, context)
                found[identifier] = {
                    "title": _component_text(resolve_json_path(payload, contract["title_field"]), "title", True),
                    "description": _component_text(resolve_json_path(payload, contract["description_field"]),
                                                   "description", contract["description_required"]),
                }
        if found.keys() != ids[kind]:
            raise ValueError("Component hydration lookup record is missing")
        lookups[kind] = found
    return lookups


def _joined_variant_value(value, context):
    """Decode scalar/object/array VARIANT values returned by Snowpark projection."""
    value = _to_python(value)
    if isinstance(value, str):
        try:
            return (json.loads(value, parse_float=Decimal)
                    if context["compiled_plan"].get("options", {}).get("parse_decimal", True)
                    else json.loads(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return value
    return value



def _forward_reference_children(source_df, target_df, contract, context, parents=None, retain_documents=False):
    """Resolve one declared RAW reference family; no native foreign identities."""
    from collections import defaultdict
    import math
    from decimal import Decimal
    def ident(value):
        if type(value) is int and value > 0:
            return str(value)
        if type(value) is str and value.isascii() and value.isdecimal() and value == str(int(value)) and int(value)>0:
            return value
        raise ValueError("Forward reference identity must be positive integral")
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError("Duplicate RAW JSON member")
            result[key]=value
        return result
    def invalid(value):raise ValueError("Nonfinite RAW JSON value")
    def validate(value):
        if isinstance(value,dict):
            if any(not isinstance(k,str) for k in value):raise ValueError("RAW keys must be strings")
            for v in value.values():validate(v)
        elif isinstance(value,list):
            for v in value:validate(v)
        elif isinstance(value,Decimal):
            if not value.is_finite():raise ValueError("Nonfinite RAW JSON value")
        elif isinstance(value,float):
            if not math.isfinite(value):raise ValueError("Nonfinite RAW JSON value")
        elif value is not None and type(value) not in (str,int,bool):raise ValueError("Unsupported RAW JSON value")
    def document(raw):
        if isinstance(raw,str):raw=json.loads(raw,object_pairs_hook=pairs,parse_float=Decimal,parse_constant=invalid)
        if not isinstance(raw,dict):raise ValueError("RAW object required")
        validate(raw);return raw
    common={'reference_field','instance_field','origin_record_id_field','provenance_field','projection','null_member_policy','blank_member_policy','allow_scalar'}
    v2 = contract.get('projection') == 'forward-raw-physical-v2'
    required = common | ({'targets'} if v2 else {'source_table','target_level_id','members'})
    chained = 'parent_binding' in contract
    if chained:
        required.add('parent_binding')
    if chained != (parents is not None) or chained and (
            not isinstance(contract['parent_binding'],str) or not contract['parent_binding']):
        raise ValueError("Forward parent input does not match declared binding")
    appended = 'append_to_record_path' in contract or 'missing_member_policy' in contract
    if appended:
        required |= {'append_to_record_path','missing_member_policy'}
    if (set(contract)!=required or contract.get('projection') not in ('forward-raw-physical-v1','forward-raw-physical-v2')
            or contract['null_member_policy']!='omit' or contract['blank_member_policy']!='reject'
            or type(contract['allow_scalar']) is not bool
            or appended and (contract.get('missing_member_policy')!='omit'
                or not isinstance(contract.get('append_to_record_path'),str)
                or not contract['append_to_record_path'].endswith('[]'))):
        raise ValueError("Invalid forward RAW physical contract")
    if appended:
        for name in ('RESOLVED_REFERENCES','MISSING_MEMBERS','NULL_MEMBERS','POPULATED_MEMBERS','EMPTY_ITEMS_OMITTED','EMITTED_ITEMS'):
            context['graph_report'].setdefault('RECORD_JOINED_'+name,0)
    specs = contract['targets'] if v2 else [{k:contract[k] for k in ('source_table','target_level_id','members')}]
    if type(specs) is not list or not specs:raise ValueError("Forward target declarations required")
    targets = {}
    for spec in specs:
        if type(spec) is not dict or set(spec)!={'source_table','target_level_id','members'}:raise ValueError("Forward target shape invalid")
        if type(spec['target_level_id']) is not int or spec['target_level_id']<=0:raise ValueError("Forward target level invalid")
        level=ident(spec['target_level_id'])
        if level in targets:raise ValueError("Duplicate target level")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*",spec['source_table']):raise ValueError("Invalid target table")
        if type(spec['members']) is not dict or not spec['members']:raise ValueError("Explicit target members required")
        if any(type(k) is not str or not k.strip() or k!=k.strip() or type(v) is not str or not v.strip() or v!=v.strip() or k!=v for k,v in spec['members'].items()):raise ValueError("Invalid declared member")
        targets[level]=spec
    if contract['allow_scalar'] and len(targets)!=1:raise ValueError("Scalar reference cannot dispatch multiple levels")
    generated=[contract[k] for k in ('instance_field','origin_record_id_field','provenance_field')]
    if not isinstance(contract['reference_field'],str) or not contract['reference_field'].strip() or contract['reference_field']!=contract['reference_field'].strip():raise ValueError("Forward source field invalid")
    if any(not isinstance(v,str) or not v.strip() or v!=v.strip() for v in generated):raise ValueError("Generated field names invalid")
    all_members=set().union(*(set(spec['members']) for spec in specs))
    if len(set(generated))!=3 or set(generated).intersection(all_members):raise ValueError("Forward projection fields collide")
    frames = target_df if v2 else {next(iter(targets)):target_df}
    if type(frames) is not dict or set(frames)!=set(targets):raise ValueError("Frozen forward snapshots mismatch")
    index=defaultdict(list)
    for level,frame in frames.items():
        for row in frame.to_local_iterator():index[(level,ident(row['SOURCE_RECORD_ID']))].append(row['CURATED_JSON'])
    by_parent={};child_index={};seen=set()
    inputs = ((owner, record['payload'], record.get('forward_document'))
              for owner, records in parents.items() for record in records) if chained else (
              (row['SOURCE_RECORD_ID'], None, row['CURATED_JSON']) for row in source_df.to_local_iterator())
    for owner_value, parent_payload, raw_input in inputs:
        owner=ident(owner_value)
        parent_identity = None
        if chained:
            parent_contract = context['lookups']['joined_contract'][contract['parent_binding']]
            parent_identity = parent_payload.get(parent_contract['instance_field'])
            if not isinstance(parent_identity,str) or not parent_identity:
                raise ValueError("Forward parent identity is missing")
        source_identity = (owner,parent_identity)
        if source_identity in seen:raise ValueError("Duplicate forward source owner")
        seen.add(source_identity);raw=document(raw_input)
        value=_restore_inline_reference_value(raw.get(contract['reference_field']))
        if value is None or value==[]:continue
        if not isinstance(value,list):raise ValueError("Forward references must be an array")
        occurrences={}
        for position,ref in enumerate(value):
            if isinstance(ref,dict):
                if set(ref)!={'ContentId','LevelId'} or type(ref['ContentId']) is not int or type(ref['LevelId']) is not int:raise ValueError("Forward reference pair invalid")
                target_id=ident(ref['ContentId'])
                target_level=ident(ref['LevelId'])
                if target_level not in targets:raise ValueError("Forward reference LevelId mismatch")
            elif type(ref) is int and contract['allow_scalar']:target_id=ident(ref);target_level=next(iter(targets))
            else:raise ValueError("Forward reference member invalid")
            occurrences.setdefault((target_level,target_id),[]).append({'source_index':position,'reference':copy.deepcopy(ref)})
        for (target_level,target_id),originals in occurrences.items():
            spec=targets[target_level]
            matches=index.get((target_level,target_id),[])
            if len(matches)!=1:raise ValueError("Forward RAW target missing or ambiguous")
            target=document(matches[0]);payload={};member_states=[]
            if appended:
                report = context['graph_report']
                report['RECORD_JOINED_RESOLVED_REFERENCES'] = report.get('RECORD_JOINED_RESOLVED_REFERENCES',0)+1
            for output,field in spec['members'].items():
                if field not in target:
                    if not appended:raise ValueError("Forward projected member missing")
                    member_states.append({'source_field':field,'output_field':output,'state':'MISSING'})
                    report['RECORD_JOINED_MISSING_MEMBERS'] = report.get('RECORD_JOINED_MISSING_MEMBERS',0)+1
                    continue
                value=target.get(field)
                member_states.append({'source_field':field,'output_field':output,'state':'NULL' if value is None else 'POPULATED'})
                if appended:
                    count = 'RECORD_JOINED_NULL_MEMBERS' if value is None else 'RECORD_JOINED_POPULATED_MEMBERS'
                    report[count] = report.get(count,0)+1
                if value is None:continue
                # Archer stores this Deviation ID as an integer, and a Finding title requires text.
                if (type(value) is int
                        and context["config"]["SOURCE_KEY"] == "source-two-control-standards"
                        and context["config"]["OSCAL_MODEL"] == "ASSESSMENT_RESULTS"
                        and contract["reference_field"] == "ISSUES_CONTROL_STANDARD"
                        and target_level == "283"
                        and spec["source_table"] == "RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_DEVIATIONS_RAW"
                        and output == field == "DEVIATION_ID"):
                    value = str(value)
                if not isinstance(value,str) or not value.strip():raise ValueError("Forward projected prose must be populated text")
                payload[output]=value
            identity=json.dumps(([contract['reference_field'],spec['source_table'],target_level,target_id] if v2 else [contract['reference_field'],spec['source_table'],target_id]),separators=(',',':'))
            if chained:
                identity=json.dumps(['forward-parent-v1',parent_identity,identity],separators=(',',':'))
            payload[contract['instance_field']]=identity
            payload[contract['origin_record_id_field']]=target_id
            payload[contract['provenance_field']]={'source_system':context['config']['SOURCE_SYSTEM_NAME'],'source_table':context['config']['SOURCE_TABLE_NAME'],'source_record_id':owner,'source_field':contract['reference_field'],'target_table':spec['source_table'],'target_content_id':target_id,'target_level_id':int(target_level),'occurrences':originals,'member_states':member_states}
            global_id=json.dumps([owner,identity],separators=(',',':'))
            child_record={'source_record_id':global_id,'payload':payload}
            if chained:
                child_record['parent_instance_key']=parent_identity
                parent_provenance = parent_payload[parent_contract['provenance_field']]
                payload[contract['provenance_field']].update(
                    parent_binding=contract['parent_binding'],
                    source_table=parent_provenance['target_table'],
                    source_record_id=parent_provenance['target_content_id'],
                    root_source_table=context['config']['SOURCE_TABLE_NAME'],
                    root_source_record_id=owner,
                    parent_provenance=copy.deepcopy(parent_provenance))
            if retain_documents:
                child_record['forward_document']=copy.deepcopy(target)
            if global_id in child_index:raise ValueError("Forward child identity collision")
            by_parent.setdefault(owner,[]).append(child_record)
            child_index[global_id]=(owner,identity)
    return by_parent,child_index

def _build_joined_record_lookups(source_df, mapping_rows, context, extra_fields=None):
    """Project only mapped child fields before streaming joined records to Python."""
    from snowflake.snowpark import functions as F

    rows_by_binding = {}
    for row in mapping_rows:
        params = _metadata_params(row)
        binding = params.get("joined_lookup")
        if not binding:
            raise ValueError("Joined-record mapping requires LOOKUP_KEY")
        rows_by_binding.setdefault(binding, []).append(row)

    if set(extra_fields or {}) - set(rows_by_binding):
        raise ValueError("Resource field requires its existing compiled joined owner")
    source_ids = source_df.select(
        F.trim(F.col("SOURCE_RECORD_ID").cast("string")).alias("_JOIN_ID")
    ).distinct()

    result, child_index = {}, {}
    contracts = context["lookups"]["joined_contract"]
    ordered_bindings = _forward_binding_order(rows_by_binding, contracts, context["compiled_plan"]["elements"])
    forward_parents = {contracts[binding]["parent_binding"] for binding in rows_by_binding
                       if contracts[binding].get("projection") in ("forward-raw-physical-v1", "forward-raw-physical-v2")
                       and "parent_binding" in contracts[binding]}
    for binding in ordered_bindings:
        binding_rows = rows_by_binding[binding]
        contract = context["lookups"]["joined_contract"][binding]
        if contract.get("projection") in ("forward-raw-physical-v1", "forward-raw-physical-v2"):
            frame = context["lookups"].get("forward_reference_sources", {}).get(binding)
            if frame is None:raise ValueError("Forward RAW frozen target snapshot missing")
            owner_paths = {row["OWNER_ELEMENT_PATH"] for row in binding_rows}
            if len(owner_paths) != 1:raise ValueError("Forward lookup requires one mapped owner path")
            parameters = context["compiled_plan"]["elements"][next(iter(owner_paths))]["parameters"]
            identity_field = parameters.get("record_joined_bindings", {}).get(binding, parameters.get("joined_instance_field"))
            if identity_field != contract.get("instance_field"):
                raise ValueError("Forward registry identity field mismatch")
            allowed_fields = (set().union(*(set(t.get("members", {})) for t in contract.get("targets", []))) if contract.get("projection") == "forward-raw-physical-v2" else set(contract.get("members", {}))) | {contract.get("provenance_field")}
            if any(row["SOURCE_FIELD_NAME"] not in allowed_fields for row in binding_rows):
                raise ValueError("Forward mapping source field is undeclared")
            parent_binding = contract.get("parent_binding")
            parents = result[parent_binding] if parent_binding else None
            result[binding], child_index[binding] = _forward_reference_children(
                source_df, frame, contract, context, parents, binding in forward_parents)
            continue
        parent_binding = contract.get("parent_binding")
        if parent_binding and parent_binding not in child_index:
            raise ValueError("Nested joined child requires its compiled parent binding")
        frame = context["lookups"].get("joined_sources", {}).get(binding)
        if frame is None:
            raise ValueError("Joined-record lookup source is unavailable: " + binding)

        columns = {str(name).strip('"').upper(): name for name in frame.columns}
        if not {"CONTENT_ID", "CURATED_JSON", "_SOURCE_RECORD_ID"}.issubset(columns):
            raise ValueError("Joined-record lookup requires parent, child identity, and CURATED_JSON")

        owner_paths = {row["OWNER_ELEMENT_PATH"] for row in binding_rows}
        if len(owner_paths) != 1:
            raise ValueError("Joined-record lookup binding must belong to one collection path")
        owner_path = next(iter(owner_paths))
        parameters = context["compiled_plan"]["elements"][owner_path]["parameters"]
        identity_field = parameters.get("joined_instance_field")
        if not identity_field:
            raise ValueError("Joined-record collection requires a registry identity field")

        required_fields = [identity_field]
        for row in binding_rows:
            field = row["SOURCE_FIELD_NAME"]
            if field not in required_fields:
                required_fields.append(field)

        for field in sorted((extra_fields or {}).get(binding, ())):
            if field not in required_fields:
                required_fields.append(field)
        json_col = F.col(columns["CURATED_JSON"])
        projected = [
            F.trim(F.col(columns["CONTENT_ID"]).cast("string")).alias("_JOIN_ID"),
            F.col(columns["_SOURCE_RECORD_ID"]).cast("string").alias("_SOURCE_RECORD_ID"),
        ]
        for field in required_fields:
            projected.append(F.get(json_col, F.lit(field)).alias(field))

        selected = frame.select(*projected)
        joined = (selected if parent_binding else
                  selected.join(source_ids, "_JOIN_ID", "inner"))
        if contract.get("require_all_children") and joined.count() != frame.count():
            raise ValueError("Required joined child has no selected parent Source record")

        by_parent, indexed_children = {}, {}
        for record in joined.to_local_iterator():
            referenced_id = str(record["_JOIN_ID"]).strip()
            if parent_binding:
                # The child references a *parent child-record Content ID*, not
                # the root Source Content ID. Resolve through the earlier
                # collection, preserving the parent collection instance key.
                owner = child_index[parent_binding].get(referenced_id)
                if owner is None:
                    raise ValueError("Nested joined child has no resolved parent record")
                parent_id, parent_instance_key = owner
            else:
                parent_id, parent_instance_key = referenced_id, None
            payload = {}
            for field in required_fields:
                raw = _to_python(record[field])
                # The accepted Topic/Section instance keys retain their original
                # projected representation. Only explicitly opted-in bindings
                # decode the projected VARIANT identity before hashing/lineage.
                if field == identity_field and not contract.get("decode_projected_identity_variant", False):
                    payload[field] = raw
                else:
                    decoded = _joined_variant_value(raw, context)
                    if field == identity_field and (not isinstance(decoded, str) or not decoded.strip()):
                        raise ValueError("Decoded joined-record identity must be nonblank text")
                    payload[field] = decoded
            source_record_id = _scalar_text(record["_SOURCE_RECORD_ID"],
                                            "Joined source identity must be scalar",
                                            "Joined source identity must be nonblank")
            identity = payload.get(identity_field)
            child_instance_key = _scalar_text(
                identity, "Joined child identity must be scalar",
                "Joined child identity must be nonblank")
            if source_record_id in indexed_children:
                raise ValueError("Duplicate joined child Content ID")
            indexed_children[source_record_id] = (parent_id, child_instance_key)
            child_record = {"source_record_id": source_record_id, "payload": payload}
            if parent_binding:
                child_record["parent_instance_key"] = parent_instance_key
            by_parent.setdefault(parent_id, []).append(child_record)

        result[binding] = by_parent
        child_index[binding] = indexed_children

    return result


def _metadata_joined_record_instances(source_id, rows, parameters, context):
    bindings = {_metadata_params(row).get("joined_lookup") for row in rows}
    if len(bindings) > 1 and None not in bindings:
        if any(context["lookups"]["joined_contract"][binding].get("projection") not in
               ("forward-raw-physical-v1", "forward-raw-physical-v2") for binding in bindings):
            raise ValueError("Multiple joined families require explicit forward contracts")
        instances, identities = [], set()
        for binding in sorted(bindings):
            family_rows = [row for row in rows if _metadata_params(row).get("joined_lookup") == binding]
            family = _metadata_joined_record_instances(source_id, family_rows, parameters, context)
            for item in family:
                if item["instance_key"] in identities:
                    raise ValueError("Joined reference family identity collision")
                identities.add(item["instance_key"]); instances.append(item)
        return instances
    if len(bindings) != 1 or None in bindings:
        raise ValueError("Joined-record collection requires exactly one lookup binding")
    binding = next(iter(bindings))
    path = rows[0]["OWNER_ELEMENT_PATH"]
    children = context.get("joined_record_lookups", {}).get(binding, {}).get(source_id, ())
    identity_field = parameters.get("joined_instance_field")
    if not identity_field:
        raise ValueError("Joined-record collection requires a registry identity field")
    contract = context["lookups"]["joined_contract"][binding]
    instances = []
    # The frozen four-level lookup has already been checked for single-parent
    # ownership. Use it as our canonical same-Catalog reference target set.
    related_rows = [row for row in rows if row["TRANSFORM_ID"] == "catalog-related-subsections"]
    related_ids = None
    all_catalog_child_owners = None
    if related_rows:
        related = context.get("joined_record_lookups", {}).get("subsections")
        if not isinstance(related, dict) or (children and source_id not in related):
            raise ValueError("Related Sub-Section requires frozen child lookup")
        # The same frozen daily snapshot already resolves child ContentIds to
        # their owning Catalog. Never assume that a reference is local.
        all_catalog_child_owners = context.get("_native_catalog_global_subsection_owners")
        if all_catalog_child_owners is None:
            # Build once from the frozen batch, not 148 times per Catalog.
            all_catalog_child_owners = {}
            for catalog_id, entries in related.items():
                for item in entries:
                    cid = item["source_record_id"]
                    if (not isinstance(cid, str) or not cid.isascii() or not cid.isdecimal()
                            or str(int(cid)) != cid or int(cid) <= 0):
                        raise ValueError("Related Sub-Section child identity must be canonical")
                    if cid in all_catalog_child_owners and all_catalog_child_owners[cid] != catalog_id:
                        raise ValueError("Related Sub-Section target has ambiguous catalog ownership")
                    all_catalog_child_owners[cid] = catalog_id
            context["_native_catalog_global_subsection_owners"] = all_catalog_child_owners
        # Empty Catalogs are valid; no targets means no emitted links.
        related_ids = {entry["source_record_id"] for entry in related.get(source_id, ())}
    for record in children:
        child = record["payload"]
        identity = resolve_json_path(child, identity_field, default=SKIP_VALUE)
        if identity is SKIP_VALUE:
            raise ValueError("Joined-record identity field is absent")
        key = _scalar_text(identity, "Joined-record identity must be scalar",
                           "Joined-record identity must be nonblank")
        origin = {"source_system": context["config"]["SOURCE_SYSTEM_NAME"],
                  "source_table": child[contract["provenance_field"]]["target_table"] if contract.get("projection") == "forward-raw-physical-v2" else contract["source_table"],
                  "source_record_id": child[contract["origin_record_id_field"]] if contract.get("origin_record_id_field") else record["source_record_id"]}
        payload, crosswalks, contributions = {}, [], []
        for row in rows:
            value = _metadata_mapped_value(row, child, context)
            if value is SKIP_VALUE:
                continue
            target = _metadata_target(row)
            property_name = _metadata_params(row).get("property_name")
            if row["TRANSFORM_ID"] == "status-crosswalk":
                crosswalks.append((row, value))
            elif row["TRANSFORM_ID"] == "catalog-related-subsections":
                # Multiple related-record fields share one native links[];
                # build sorted unique hrefs rather than conflicting writers.
                if binding != "subsections" or target != "links" or related_ids is None:
                    raise ValueError("Related links require a Sub-Section owner")
                links = payload.setdefault("links", [])
                existing = {(link.get("href"), link.get("rel")) for link in links}
                current = record["source_record_id"]
                for cid in value:
                    if cid == current:
                        reason = "SELF_REFERENCE_PENDING"
                    elif cid not in related_ids:
                        reason = ("CROSS_CATALOG_REFERENCE_PENDING"
                                  if cid in all_catalog_child_owners else
                                  "UNKNOWN_TARGET_REFERENCE_PENDING")
                    else:
                        reason = None
                    if reason is not None:
                        # No fabricated external URI, invalid local fragment,
                        # or silently discarded field value. Keep a value-free
                        # aggregate gap and prevent Cell 7 COMMIT through its
                        # existing LINEAGE_GAP_COUNT safety contract.
                        metric = "NATIVE_CATALOG_SUBSECTION_" + reason
                        context["graph_report"][metric] = context["graph_report"].get(metric, 0) + 1
                        context["graph_report"]["LINEAGE_GAPS"] += 1
                        samples = context["graph_report"]["LINEAGE_GAP_SAMPLES"]
                        if len(samples) < 25:
                            samples.append({"reason": reason, "source_field": row["SOURCE_FIELD_NAME"],
                                            "target_path": "catalog.groups[].groups[].groups[].links"})
                        continue
                    # Keep in sync with the already-approved group id policy:
                    # g-subsections-{original Archer CONTENT_ID}.
                    href = "#" + _oscal_token("g-subsections-" + cid)
                    link = {"href": href, "rel": "related"}
                    if (href, "related") not in existing:
                        links.append(link)
                        existing.add((href, "related"))
                        context["graph_report"]["NATIVE_CATALOG_RELATED_SUBSECTION_LINKS"] = (
                            context["graph_report"].get("NATIVE_CATALOG_RELATED_SUBSECTION_LINKS", 0) + 1)
                links.sort(key=lambda item: (item["href"], item["rel"]))
            elif row["TRANSFORM_ID"] == "catalog-owner-procedure-props":
                procedure_binding = _owner_procedure_binding(row, context)
                payload = preview_merge_on_existing_owner(
                    payload, source_field_guid=procedure_binding["field_guid"],
                    namespace_mode=procedure_binding["namespace_mode"], property_name=procedure_binding["property_name"],
                    raw_procedure_references=value)
            elif target == "props" and _metadata_params(row).get("scalar_array_property_key"):
                _scalar_array_property_contract(row,context)
                for member in value:
                    prop = _oscal_prop(property_name,member)
                    if _metadata_params(row).get("property_namespace"):
                        prop["ns"] = _metadata_params(row)["property_namespace"]
                    payload.setdefault("props", []).append(prop)
            elif target in {"props", "parts"} and property_name:
                if target == "parts" and row["TRANSFORM_ID"] == "prose-direct":
                    # Preserve Direct narrative/HTML exactly, including leading
                    # and trailing whitespace. Other Topic/Section text and
                    # business-property mappings retain accepted scalar rules.
                    prose = _metadata_text(value, "Direct prose")
                    payload.setdefault("parts", []).append(
                        {"name": property_name, "prose": prose})
                else:
                    values = _oscal_property_values(value)
                    if len(values) != 1:
                        raise ValueError("Joined embedded property or part requires exactly one scalar")
                    if target == "props":
                        prop = _oscal_prop(property_name, values[0])
                        if _metadata_params(row).get("property_namespace"):
                            prop["ns"] = _metadata_params(row)["property_namespace"]
                        payload.setdefault("props", []).append(prop)
                    else:
                        # Accepted legacy prose mappings retain trimmed output.
                        payload.setdefault("parts", []).append(
                            {"name": property_name, "prose": values[0]})
            else:
                # The previous Archer TOPIC_ID/SECTION_ID/SUB_SECTION_ID fields
                # are often unique only inside their parent, not Catalog-wide.
                # OSCAL group/@id is document-instance unique. A stable scoped
                # native ID uses the original child ContentId; retain the exact
                # Archer business ID in the explicitly named property below.
                if row["TRANSFORM_ID"] == "oscal-scoped-group-id":
                    record_id = record["source_record_id"]
                    if not isinstance(record_id, str) or not record_id.isascii() or not record_id.isdecimal() or str(int(record_id)) != record_id or int(record_id) <= 0:
                        raise ValueError("Scoped group id requires positive Archer source record id")
                    if binding not in {"topics", "sections", "subsections"}:
                        raise ValueError("Scoped group id requires reviewed joined-record binding")
                    scoped = _oscal_token("g-" + binding + "-" + record_id)
                    _assign_mapped(payload, row, target, scoped, contributions, context, origin)
                else:
                    _assign_mapped(payload, row, target, value, contributions, context, origin)
                if row["TRANSFORM_ID"] in {"oscal-token", "oscal-scoped-group-id"} and property_name:
                    original = resolve_json_path(child, row["SOURCE_FIELD_NAME"])
                    if not isinstance(original, str) or not original.strip():
                        raise ValueError("Original joined ID must be nonblank text")
                    if row["TRANSFORM_ID"] == "oscal-scoped-group-id" or value != original:
                        payload.setdefault("props", []).append(_oscal_prop(property_name, original))
        for row, members in crosswalks:
            for member, value in members.items():
                _assign_mapped(payload, row, member, value, contributions, context, origin,
                               preserve_existing=member == "remarks")
        child_id_property = contract.get("child_record_id_property")
        if child_id_property:
            child_id = record["source_record_id"]
            if not isinstance(child_id, str) or not child_id.strip():
                raise ValueError("Joined child provenance identity is missing")
            payload.setdefault("props", []).append(_oscal_prop(child_id_property, child_id))
        if any(not _has_value(_metadata_get(payload, member))
               for member in parameters.get("required_members", ())):
            if contract.get("require_all_children"):
                raise ValueError("Required joined child is missing native group members")
            context["graph_report"]["SKIPPED_JOINED_RECORDS"] = context["graph_report"].get("SKIPPED_JOINED_RECORDS", 0) + 1
            continue
        if contract.get("require_all_children"):
            group_id = payload.get("id")
            if any(existing["payload"].get("id") == group_id
                   or existing["instance_key"] == key for existing in instances):
                raise ValueError("Joined children have duplicate group identity")
            _validate_joined_property_collisions(payload.get("props", ()), path, context)
            part_names = [part["name"] for part in payload.get("parts", ())]
            if len(part_names) != len(set(part_names)):
                raise ValueError("Joined child part names collide")
        parent_instance_key = (record.get("parent_instance_key")
                               if contract.get("parent_binding")
                               else _metadata_parent_key(parameters, source_id))
        if contract.get("parent_binding") and (
                not isinstance(parent_instance_key, str) or not parent_instance_key.strip()):
            raise ValueError("Nested joined child requires its parent instance identity")
        _append_unique_collection_instance(instances, {
            "instance_key": key, "payload": payload,
            "parent_instance_key": parent_instance_key,
            "contributions": contributions})
    return instances


def _metadata_party_uuid(group, source_record_id, identifier, context):
    # Cell 3 permits one source namespace per linked model; preserve its accepted seed.
    return _deterministic_uuid(context["config"]["SOURCE_SYSTEM_NAME"], source_record_id, "party", identifier)


def _metadata_party_instances(path, source_obj, source_id, operator, parameters, context):
    group = next(group for group in context["compiled_plan"]["reference_groups"]
                 if path in (group["roles_path"], group["parties_path"], group["assignments_path"]))
    cache = context.setdefault("_metadata_reference_cache", {})
    if group["assignments_path"] not in cache:
        roles, parties, assignments, assignment_lineage = {}, {}, {}, {}
        for row in context["mappings_by_path"].get(group["assignments_path"], ()):
            value = _metadata_mapped_value(row, source_obj, context)
            if value is SKIP_VALUE:
                continue
            # An explicitly empty user/group selection is absence, not a person.
            # Do not hide null, malformed, or populated unresolved references.
            if (isinstance(value, dict) and {"UserList", "GroupList"}.intersection(value)
                    and value.get("UserList", []) == [] and value.get("GroupList", []) == []):
                continue
            params, extracted = _metadata_params(row), _extract_reference_ids(value)
            members = extracted if isinstance(extracted, list) else [extracted]
            party_ids = {}
            for item in members:
                if item is None:
                    continue
                identifier = _party_reference_identifier(item)
                party_uuid = _metadata_party_uuid(group, source_id, identifier, context)
                candidate = _party_payload(item, party_uuid, group["party_type"], context)
                parties[party_uuid] = (
                    _merge_party_payload(parties[party_uuid], candidate)
                    if party_uuid in parties else candidate
                )
                party_ids.setdefault(party_uuid, None)
            if not party_ids:
                continue
            role, title = params["role_id"], params["role_title"]
            if roles.setdefault(role, title) != title:
                raise ValueError("Role identity resolves to conflicting titles")
            field, references = assignments.setdefault(role, (row["SOURCE_FIELD_NAME"], {}))
            references.update(party_ids)
            if row.get("LINEAGE_REQUIRED_FLAG"):
                assignment_lineage.setdefault(role, {}).setdefault(row["SOURCE_FIELD_NAME"], None)

        assignment_values = []
        for role, (field, references) in assignments.items():
            payload = {"role-id": role, "party-uuids": list(references)}
            source_fields = list(assignment_lineage.get(role, ()))
            if source_fields:
                payload["props"] = [_oscal_prop("source-field", source_field)
                                    for source_field in source_fields]
                context["graph_report"]["LINEAGE_PROPS"] += len(source_fields)
            assignment_values.append((field, payload))

        cache[group["assignments_path"]] = {
            "roles": [(key, {"id": key, "title": title}) for key, title in roles.items()],
            "parties": [(key, payload) for key, payload in parties.items()],
            "assignments": assignment_values,
        }
    family = cache[group["assignments_path"]]
    return [{"instance_key": key, "payload": payload,
             "contributions": [],
             "parent_instance_key": _metadata_parent_key(parameters, source_id)}
            for key, payload in family[operator]]


def _metadata_reference_instances(source_obj, source_id, rows, parameters, context):
    references, contributors = {}, {}
    for row in rows:
        value, params = _metadata_mapped_value(row, source_obj, context), _metadata_params(row)
        if value is SKIP_VALUE:
            continue
        for identifier in _component_reference_content_ids(value):
            _capture_contribution(contributors.setdefault(identifier, []), row, "", context)
            previous = references.get(identifier)
            if previous and previous["reference_type"] != params["reference_type"]:
                raise ValueError("Referenced identity has contradictory types")
            if previous is None or params.get("hydrate_lookup"):
                references[identifier] = params
    result = []
    for identifier, params in sorted(references.items()):
        payload = {"type": params["reference_type"]} if params["reference_type"] else {}
        if params.get("hydrate_lookup"):
            hydrated = context["component_hydration_lookups"][params["reference_type"]][identifier]
            payload["title"] = hydrated["title"]
            if hydrated["description"] is not None:
                payload["description"] = hydrated["description"]
        result.append({"instance_key": identifier, "payload": payload,
                       "contributions": contributors.get(identifier, []),
                       "parent_instance_key": _metadata_parent_key(parameters, source_id)})
    return result


def _metadata_descendant_has_value(path, source_obj, context):
    prefix = path + "."
    for mapped_path, rows in context["mappings_by_path"].items():
        if mapped_path != path and not mapped_path.startswith(prefix):
            continue
        for row in rows:
            params = _metadata_params(row)
            raw = (context["config"].get(row["SOURCE_FIELD_NAME"], SKIP_VALUE)
                   if params.get("value_source") == "CONFIG"
                   else resolve_json_path(source_obj, row["SOURCE_FIELD_NAME"], default=SKIP_VALUE))
            if raw is not SKIP_VALUE and _has_value(raw):
                return True
    return False


def _validated_link_array(values):
    """Shared accepted link-object contract; preserves input order and source values."""
    if not isinstance(values, list):
        raise ValueError("Link collection requires an array")
    seen = set()
    result = []
    for link in values:
        link = _to_python(link)
        if not isinstance(link, dict) or set(link) != {"Id", "Name", "SortOrder", "Url"}:
            raise ValueError("SOURCE_LINKS member must contain Id, Name, SortOrder and Url")
        identity = link["Id"]
        if (isinstance(identity, bool) or not isinstance(identity, (int, float, Decimal))
                or not math.isfinite(float(identity)) or int(identity) != identity
                or identity <= 0):
            raise ValueError("SOURCE_LINKS.Id requires a positive integral identifier")
        link_id = str(int(identity))
        if link_id in seen:
            raise ValueError("SOURCE_LINKS has duplicate native resource identities")
        seen.add(link_id)
        title = link["Name"]
        if not isinstance(title, str) or not title.strip() or any(c in title for c in "\r\n"):
            raise ValueError("SOURCE_LINKS.Name requires a single-line title")
        url = link["Url"]
        if not isinstance(url, str) or not url or url != url.strip() or any(c.isspace() for c in url):
            raise ValueError("SOURCE_LINKS.Url requires nonblank canonical URI text")
        try:
            uri = urlsplit(url)
            if uri.scheme not in {"http", "https"} or not uri.hostname:
                raise ValueError("not an HTTP URL")
            # A malformed explicit port is not a valid RFC network URI.
            _ = uri.port
        except ValueError:
            raise ValueError("SOURCE_LINKS.Url requires a valid HTTP(S) URI") from None
        order = link["SortOrder"]
        if (isinstance(order, bool) or not isinstance(order, (int, float, Decimal))
                or not math.isfinite(float(order))):
            raise ValueError("SOURCE_LINKS.SortOrder requires a finite number")
        result.append((link, link_id, title, url, order))
    return result


def _link_array_markup(value):
    """Render exact link labels/destinations as literal CommonMark, in input order."""
    import string
    value = _to_python(value)
    if value is None or value == []:
        return SKIP_VALUE
    rendered = []
    for link, link_id, title, url, order in _validated_link_array(value):
        # Bounded ASCII URI rendering contract. Never repair/encode source text.
        if (not url.isascii() or any(ord(c) < 33 or ord(c) == 127 for c in url)
                or any(c in url for c in '<>"{}|^`\\[]')
                or url.count('#') > 1 or urlsplit(url).netloc.count('@') > 1
                or re.search(r"%(?![0-9A-Fa-f]{2})", url)
                or any(ord(c) < 32 or ord(c) == 127 for c in title)):
            raise ValueError("Link markup requires safe literal title and URI syntax")
        label = "".join("\\" + c if c in string.punctuation else c for c in title)
        # CommonMark decodes character references in destinations. Escape ampersands
        # so source entity-like text survives exactly, without URI normalization.
        destination = url.replace("&", "\\&")
        rendered.append("- [" + label + "](<" + destination + ">)")
    return "\n".join(rendered) if rendered else SKIP_VALUE


def _catalog_source_link_resources(source_obj, rows, context):
    """One Source-level CSV rule yields zero or more native Back Matter resources."""
    if len(rows) != 1:
        raise ValueError("Back Matter source collection requires one exact source mapping")
    values = _metadata_mapped_value(rows[0], source_obj, context)
    if values is SKIP_VALUE:
        return []
    if not isinstance(values, list):
        raise ValueError("Back Matter link source must be an array")
    result = []
    for link, link_id, title, url, order in _validated_link_array(values):
        payload = {
            "title": title,
            "rlinks": [{"href": url}],
            "props": [_oscal_prop("archer-link-id", link_id),
                      _oscal_prop("archer-sort-order", str(order))],
        }
        result.append({"instance_key": "source-link-" + link_id, "payload": payload,
                       "parent_instance_key": "singleton", "contributions": []})
    context["graph_report"]["CATALOG_BACK_MATTER_RESOURCE_COUNT"] = (
        context["graph_report"].get("CATALOG_BACK_MATTER_RESOURCE_COUNT", 0) + len(result))
    return result



def _metadata_resource_collection(source_obj, source_id, rows, context):
    """Assemble explicit resource families without changing accepted link identities."""
    legacy = [row for row in rows if row["TRANSFORM_ID"] == "catalog-source-links"]
    result = _catalog_source_link_resources(source_obj, legacy, context) if legacy else []
    additional = []
    for row in rows:
        if row["TRANSFORM_ID"] == "catalog-source-links":
            continue
        params, field = _metadata_params(row), row["SOURCE_FIELD_NAME"]
        binding = params.get("joined_lookup")
        owners = context["joined_record_lookups"].get(binding, {}).get(source_id, ()) if binding else (
            {"source_record_id": source_id, "payload": source_obj},)
        for owner in owners:
            value = _metadata_mapped_value(row, owner["payload"], context)
            if value is SKIP_VALUE:
                continue
            owner_table = (context["lookups"]["joined_contract"][binding]["source_table"]
                           if binding else context["config"]["RAW_TABLE"])
            identity = [owner_table, owner["source_record_id"], field, binding, None, None]
            if params["target"] == "base64":
                payloads = [(identity, {"base64": value})]
            else:
                lookup = params["resource_lookup"]
                title_row = context["_resource_title_rows"][lookup]
                targets = context["joined_record_lookups"].get(lookup, {}).get(source_id, ())
                by_id = {}
                for target in targets:
                    target_id = target["source_record_id"]
                    if target_id in by_id:
                        raise ValueError("Resource citation target identity is ambiguous")
                    by_id[target_id] = target
                payloads = []
                for reference_id in value:
                    target = by_id.get(reference_id)
                    if target is None:
                        raise ValueError("Resource citation target is absent from its exact source parent")
                    raw_title = resolve_json_path(target["payload"], title_row["SOURCE_FIELD_NAME"], default=SKIP_VALUE)
                    title = (_metadata_transform(title_row, raw_title, context)
                             if raw_title is not SKIP_VALUE else SKIP_VALUE)
                    if not isinstance(title, str) or not title.strip():
                        raise ValueError("Resource citation requires the actual mapped target title")
                    item_identity = list(identity)
                    item_identity[3:] = [lookup, params["reference_level"], reference_id]
                    payloads.append((item_identity, {"title": title, "citation": {"text": title}}))
            for item_identity, payload in payloads:
                payload["props"] = [_oscal_prop("source-field", field)]
                additional.append({"instance_key": "field-resource:" + json.dumps(item_identity, separators=(",", ":")),
                                   "payload": payload, "parent_instance_key": "singleton", "contributions": []})
    keys = [item["instance_key"] for item in additional]
    if len(keys) != len(set(keys)):
        raise ValueError("Resource mappings have duplicate owner/field/reference identities")
    result.extend(sorted(additional, key=lambda item: item["instance_key"]))
    context["graph_report"]["CATALOG_BACK_MATTER_RESOURCE_COUNT"] = (
        context["graph_report"].get("CATALOG_BACK_MATTER_RESOURCE_COUNT", 0) + len(additional))
    return result


def _source_property_complete_spec(config):
    """Resolve the finite lifecycle from the independent frozen metadata snapshot."""
    spec = config.get("SOURCE_PROPERTY_LIFECYCLE_SPEC")
    if not spec or spec.get("version") != _SOURCE_PROPERTY_LIFECYCLE_VERSION:
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_ROUTE_INVALID")
    return copy.deepcopy(spec)

def _source_property_complete_prepare(context):
    """Validate the complete exact mapping set before reading any Source records."""
    declaration = context["route"]
    if not declaration.get("property_identity") or declaration["property_identity"].get("version") == "singleton-properties-v1":
        return
    config = context["config"]
    spec = _source_property_complete_spec(config)
    allowed = dict(spec["fields"], **spec["member_fields"])
    selected = {}
    for item in context["mapping_rows"]:
        if item["OWNER_ELEMENT_PATH"] != spec["path"]:
            continue
        field = item["SOURCE_FIELD_NAME"]
        expected = allowed.get(field)
        if expected is None:
            # Ordinary approved fields keep value identity and acquire no deletion authority.
            if _metadata_params(item).get("property_name") in {value[1] for value in allowed.values()}:
                previous = context.get("_owner_procedure_bindings", {}).get(_owner_procedure_key(spec["path"], spec["procedure_contract"]["source_field"], spec["procedure_contract"].get("joined_lookup")))
                if item["TRANSFORM_ID"] != "catalog-owner-procedure-props" or previous is None or _owner_procedure_binding(item,context)["namespace"] == previous["namespace"]:
                    raise ValueError("SOURCE_PROPERTY_LIFECYCLE_PROPERTY_NAME_COLLISION")
            continue
        if (field in selected
                or item.get("LOOKUP_KEY") or item["TRANSFORM_ID"] != expected[0]
                or _metadata_params(item).get("property_name") != expected[1]
                or (item.get("NULL_POLICY") or "omit") != "omit"
                or item.get("LINEAGE_REQUIRED_FLAG")
                or item.get("REPRESENTATION") != "properties"
                or item.get("VALUE_SOURCE") != "FIELD"):
            raise ValueError("SOURCE_PROPERTY_LIFECYCLE_MAPPING_CONTRACT_INVALID")
        if any(item["source_field"] == field and item["owner_path"] == spec["path"]
               for item in declaration.get("scalar_array_properties", [])):
            if _scalar_array_property_contract(item, context) is None:
                raise ValueError("SOURCE_PROPERTY_LIFECYCLE_ARRAY_CONTRACT_REQUIRED")
        selected[field] = expected
    if selected != allowed:
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_MAPPING_SET_INCOMPLETE")
    declaration = next((d for d in context["compiled_plan"].get("owner_procedure_props", {}).get("contracts", {}).values() if d["owner_path"] == spec["path"] and all(d.get(k) == v for k,v in spec["procedure_contract"].items())), None)
    if (not isinstance(declaration, dict)
            or any(declaration.get(key) != value for key, value in spec["procedure_contract"].items())):
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_PROCEDURE_CONTRACT_INVALID")
    binding = context.get("_owner_procedure_bindings", {}).get(_owner_procedure_key(spec["path"], declaration["source_field"], declaration["joined_lookup"]))
    if (not isinstance(binding, dict)
            or any(binding.get(key) != value for key, value in spec["procedure_contract"].items()
                   if key in ("source_field", "namespace_mode", "property_name"))
            or binding.get("namespace") != UUID(binding.get("field_guid", "")).urn):
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_PROCEDURE_NAMESPACE_INVALID")
    namespace = binding["namespace"]
    previous_namespace = config.get("SOURCE_PROPERTY_PROCEDURE_NAMESPACE")
    if previous_namespace is not None and previous_namespace != namespace:
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_PROCEDURE_NAMESPACE_CHANGED")
    config["SOURCE_PROPERTY_PROCEDURE_NAMESPACE"] = namespace
    previous = config.get("SOURCE_PROPERTY_LIFECYCLE_SPEC")
    if previous is not None and previous != spec:
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_SPEC_CONFLICT")
    config["SOURCE_PROPERTY_LIFECYCLE_SPEC"] = spec


def _source_property_lifecycle_row(row, context, path):
    declaration = context["route"].get("property_identity")
    if not declaration or declaration.get("version") == "singleton-properties-v1" or path != declaration["path"]:
        return False
    spec = context["config"].get("SOURCE_PROPERTY_LIFECYCLE_SPEC")
    if not isinstance(spec, dict) or spec.get("version") != _SOURCE_PROPERTY_LIFECYCLE_VERSION:
        raise ValueError("SOURCE_PROPERTY_LIFECYCLE_PREPARE_REQUIRED")
    return row["SOURCE_FIELD_NAME"] in spec["fields"] and not row.get("LOOKUP_KEY")


def _stable_property_prepare(context):
    """Validate opt-in singleton field identities against the exact mapping contract."""
    life = context["route"].get("property_identity", {})
    fields = life.get("stable_fields", [])
    reconcile = life.get("reconcile_fields", [])
    if not fields and not reconcile:
        context["config"].pop("STABLE_PROPERTY_CONTRACT", None)
        context["stable_property_fields"] = set()
        return
    if (type(fields) is not list or type(reconcile) is not list or type(life.get("migrate_value_ids", False)) is not bool
            or type(life.get("reconcile_missing_values", False)) is not bool):
        raise ValueError("INVALID_STABLE_PROPERTY_CONTRACT")
    if life.get('source_document_contract') != 'complete-curated-json-v1':
        raise ValueError("PROPERTY_RECONCILIATION_REQUIRES_COMPLETE_DOCUMENT_CONTRACT")
    if (life.get("version") not in {"singleton-properties-v1", _SOURCE_PROPERTY_LIFECYCLE_VERSION}
            or getattr(globals().get("validate_and_load_oscal"), "_stable_property_identity_version", None) != "singleton-properties-v1"):
        raise ValueError("STABLE_PROPERTY_MATCHED_LOADER_REQUIRED")
    guaranteed = {"json-text", "json-value", "text", "timestamp", "canonical-text", "prose-direct",
                  "date", "identifier", "oscal-token", "oscal-scoped-group-id", "scalar-score"}
    identities, names = set(), set()
    for entry in fields + reconcile:
        is_new = entry in fields
        expected_keys = {"path", "field", "transform", "name", "namespace"} | (set() if is_new else {'identity'})
        if not isinstance(entry, dict) or set(entry) != expected_keys:
            raise ValueError("INVALID_STABLE_PROPERTY_CONTRACT")
        identity = (entry["path"], entry["field"])
        named = (entry["path"], entry["name"], entry["namespace"])
        if (identity in identities or (is_new and named in names) or (is_new and entry["transform"] not in guaranteed)
                or (not is_new and entry['identity'] not in {'existing-singleton','existing-field','value-member'})):
            raise ValueError("STABLE_PROPERTY_CARDINALITY_OR_COLLISION")
        identities.add(identity)
        names.add(named)
        matches = [row for row in context["mapping_rows"]
                   if (row["OWNER_ELEMENT_PATH"], row["SOURCE_FIELD_NAME"]) == identity]
        if len(matches) != 1:
            raise ValueError("STABLE_PROPERTY_MAPPING_MISSING_OR_DUPLICATE")
        row = matches[0]
        params = _metadata_params(row)
        element = context["compiled_plan"]["elements"][entry["path"]]
        if (row["TRANSFORM_ID"] != entry["transform"] or row.get("LOOKUP_KEY")
                or (row["VALUE_SOURCE"] or "FIELD") != "FIELD" or element["operator"] != "properties"
                or row.get('LINEAGE_REQUIRED_FLAG')
                or (is_new and params.get("scalar_array_property_key")) or element["parameters"].get("include_uuid")
                or (is_new and element["parameters"]["registry_contract"]["instance_key_rule"] != "SOURCE_FIELD_NAME+VALUE")
                or (params.get("property_name") or _stable_property_name(entry["field"])) != entry["name"]
                or params.get("property_namespace") != entry["namespace"]):
            raise ValueError("STABLE_PROPERTY_MAPPING_CONTRACT_CHANGED")
        if not is_new:
            if params.get('scalar_array_property_key'):
                _scalar_array_property_contract(row, context)
            expected_identity = ('existing-singleton' if entry['field'] in life.get('fields', {})
                                 else 'existing-field' if element['parameters']['registry_contract']['instance_key_rule']=='SOURCE_FIELD_NAME' and not params.get('scalar_array_property_key')
                                 else 'value-member')
            if entry['identity'] != expected_identity:
                raise ValueError("PROPERTY_RECONCILIATION_IDENTITY_CONTRACT_CHANGED")
        for other in context["mapping_rows"]:
            if other is row or other["OWNER_ELEMENT_PATH"] != entry["path"]:
                continue
            other_params = _metadata_params(other)
            if (is_new and (other_params.get("property_name") or _stable_property_name(other["SOURCE_FIELD_NAME"])) == entry["name"]
                    and other_params.get("property_namespace") == entry["namespace"]):
                raise ValueError("STABLE_PROPERTY_NAME_NAMESPACE_COLLISION")
    context["stable_property_fields"] = {(e['path'],e['field']) for e in fields}
    context['reconcile_property_fields'] = bool(reconcile or fields)
    context["config"]["STABLE_PROPERTY_CONTRACT"] = copy.deepcopy({
        "fields": fields, "migrate_value_ids": life.get("migrate_value_ids", False),
        "reconcile_missing_values": life.get("reconcile_missing_values", False),
        "reconcile_fields": reconcile, "source_document_contract": life.get('source_document_contract')})


def _metadata_instances(source_obj, source_id, registry_row, context):
    path = registry_row["element_path"]
    specification = context["compiled_plan"]["elements"].get(path)
    if specification is None:
        return []
    operator, parameters = specification["operator"], specification["parameters"]
    rows, parent = context["mappings_by_path"].get(path, ()), _metadata_parent_key(parameters, source_id)
    if rows:
        _source_property_lifecycle_row(rows[0], context, path)
    if path == "catalog.back-matter":
        # Back Matter is optional in OSCAL. Create it only for a Source record
        # with actual resources; never generate empty placeholder objects.
        mapped = context["mappings_by_path"].get("catalog.back-matter.resources[]", ())
        if any(row["TRANSFORM_ID"] in {"resource-base64", "resource-citation"} for row in mapped):
            resources = _metadata_resource_collection(source_obj, source_id, mapped, context)
            context["_resource_instances"] = (source_id, resources)
            if not resources:
                return []
        else:
            if len(mapped) != 1:
                raise ValueError("Catalog Back Matter requires exactly one active source-link field")
            present = resolve_json_path(source_obj, mapped[0]["SOURCE_FIELD_NAME"], default=SKIP_VALUE)
            if present is SKIP_VALUE or not _has_value(present):
                return []
            if not isinstance(present, list):
                raise ValueError("Back Matter source field must be an array")
    if operator == "catalog-resources":
        if any(row["TRANSFORM_ID"] in {"resource-base64", "resource-citation"} for row in rows):
            cached = context.get("_resource_instances")
            if cached is None or cached[0] != source_id:
                raise ValueError("Resource collection requires its current source parent assembly")
            return cached[1]
        return _catalog_source_link_resources(source_obj, rows, context)
    if operator == "inline-links":
        return _inline_link_instances(source_obj, source_id, rows, parameters, context)
    if operator in {"roles", "parties", "assignments"}:
        return _metadata_party_instances(path, source_obj, source_id, operator, parameters, context)
    if operator == "catalog-controls":
        return []  # Assembled once in bulk after the complete existing owner graph.
    if operator == "references":
        return _metadata_reference_instances(source_obj, source_id, rows, parameters, context)
    if operator == "joined-records":
        return _metadata_joined_record_instances(source_id, rows, parameters, context)
    appended_rows = {}
    if parameters.get("record_joined_bindings"):
        local_rows = []
        for row in rows:
            binding = _metadata_params(row).get("joined_lookup")
            if binding:
                if binding not in parameters["record_joined_bindings"]:
                    raise ValueError("Appended record lookup ownership mismatch")
                appended_rows.setdefault(binding, []).append(row)
            else:
                local_rows.append(row)
        rows = local_rows
    payload, instances, crosswalks, contributions = {}, [], [], []
    for row in rows:
        value = _metadata_mapped_value(row, source_obj, context)
        if value is SKIP_VALUE:
            continue
        field, target = row["SOURCE_FIELD_NAME"], _metadata_target(row)
        if operator == "properties" and row["TRANSFORM_ID"] == "catalog-owner-procedure-props":
            binding = _owner_procedure_binding(row, context)
            for prop in preview_guid_named_procedure_props(
                    source_field_guid=binding["field_guid"], namespace_mode=binding["namespace_mode"],
                    property_name=binding["property_name"], raw_procedure_references=value):
                key = field + ":" + _deterministic_hash("source-field-value-v1", field, prop["value"])
                _append_unique_collection_instance(instances, {
                    "instance_key": key, "payload": prop, "contributions": [],
                    "parent_instance_key": parent})
        elif operator in {"properties", "observations"}:
            values = [None] if value is None else _oscal_property_values(value)
            source_singleton = _source_property_lifecycle_row(row, context, path)
            stable_singleton = (path, field) in context.get("stable_property_fields", set())
            field_identity = (source_singleton or stable_singleton or operator == "observations" or
                              parameters["registry_contract"].get("instance_key_rule") == "SOURCE_FIELD_NAME" and not _metadata_params(row).get("scalar_array_property_key"))
            if field_identity and len(values) != 1:
                raise ValueError("One scalar value is required per field identity")
            for item in values:
                property_name = _metadata_params(row).get("property_name") or _stable_property_name(field)
                prop = _oscal_prop(property_name, item)
                if _metadata_params(row).get("property_namespace"):
                    prop["ns"] = _metadata_params(row)["property_namespace"]
                item_contributions = []
                _capture_contribution(item_contributions, row,
                                      "props.0.value" if operator == "observations" else "value", context)
                item_payload = {"props": [prop]} if operator == "observations" else prop
                key = ("source-field-singleton-v1:" + field if stable_singleton else
                       context["config"]["SOURCE_PROPERTY_LIFECYCLE_SPEC"]["singleton_prefix"] + field if source_singleton else
                       field if field_identity else field + ":" + _deterministic_hash("source-field-value-v1", field, item))
                _append_unique_collection_instance(instances, {"instance_key": key, "payload": item_payload,
                                                               "contributions": item_contributions,
                                                               "parent_instance_key": "singleton" if source_singleton else parent})
        elif operator == "named-parts":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Named part prose must be nonblank text")
            name = _metadata_params(row)["property_name"]
            # One configured part name identifies one authored part per owner.
            # Different source fields may not silently coalesce into that part.
            if any(item["instance_key"] == name for item in instances):
                raise ValueError("Named part ownership is ambiguous")
            part = {"name": name, "prose": value}
            if _metadata_params(row).get("property_namespace"):
                part["ns"] = _metadata_params(row)["property_namespace"]
            instances.append({"instance_key": name,
                              "payload": part,
                              "parent_instance_key": parent, "contributions": []})
        elif operator == "values":
            for member in (value if isinstance(value, list) else [value]):
                item_payload = copy.deepcopy(member) if isinstance(member, dict) else {}
                raw = _metadata_get(item_payload, target) if isinstance(member, dict) else member
                values = _oscal_property_values(raw)
                if len(values) != 1:
                    raise ValueError("Value identity requires exactly one scalar")
                normalized = values[0]
                cursor, tokens = item_payload, target.split(".")
                for token in tokens[:-1]:
                    cursor = cursor.setdefault(token, {})
                cursor[tokens[-1]] = normalized
                item_contributions = []
                _capture_contribution(item_contributions, row, target, context)
                _append_unique_collection_instance(instances, {"instance_key": _deterministic_hash("value-v1", normalized),
                                                               "payload": item_payload, "parent_instance_key": parent,
                                                               "contributions": item_contributions})
        elif row["TRANSFORM_ID"] == "status-crosswalk":
            crosswalks.append((row, value))
        else:
            _assign_mapped(
                payload, row, target, value, contributions, context,
                null_coalesce=(
                    parameters.get("preserve_explicit_null_members", False)
                    and row["TRANSFORM_ID"] == "security-objective"
                ),
            )
    for row, members in crosswalks:
        for member, value in members.items():
            _assign_mapped(payload, row, member, value, contributions, context,
                           preserve_existing=member == "remarks")
    missing_required = [
        member for member in parameters.get("required_members", ())
        if not _has_value(_metadata_get(payload, member))
    ]
    # Incomplete native warehouse JSON is deliberately not an OSCAL export.
    # Explicit JSON nulls are retained; absent source keys are never fabricated.
    if missing_required and not parameters.get("preserve_explicit_null_members", False):
        if parameters.get("optional_assembly"):
            return []
        raise ValueError("Required payload member is missing")
    if operator == "optional-record":
        if payload or _metadata_descendant_has_value(path, source_obj, context):
            instances.append({"instance_key": source_id, "payload": payload, "parent_instance_key": parent,
                              "contributions": contributions})
    elif operator in {"object", "record"} and (payload or parameters.get("materialize_empty") or operator == "record"):
        instances.append({"instance_key": source_id if operator == "record" else "singleton",
                          "payload": payload, "parent_instance_key": parent, "contributions": contributions})
    keys = {item["instance_key"] for item in instances}
    for binding, mapped in sorted(appended_rows.items()):
        joined_parameters = dict(parameters, joined_instance_field=parameters["record_joined_bindings"][binding])
        for item in _metadata_joined_record_instances(source_id, mapped, joined_parameters, context):
            if item["instance_key"] in keys:
                raise ValueError("Appended record identity collides with an existing collection member")
            keys.add(item["instance_key"])
            if not item["payload"]:
                report = context["graph_report"]
                report["RECORD_JOINED_EMPTY_ITEMS_OMITTED"] = report.get("RECORD_JOINED_EMPTY_ITEMS_OMITTED",0)+1
                continue
            instances.append(item)
            report = context["graph_report"]
            report["RECORD_JOINED_EMITTED_ITEMS"] = report.get("RECORD_JOINED_EMITTED_ITEMS",0)+1
    return instances


def _metadata_uuid(path, instance, source_system, source_table, source_id, model_key, context):
    if context["compiled_plan"]["elements"][path]["parameters"].get("uuid_from_instance"):
        return instance["instance_key"]
    return _deterministic_uuid(context["config"]["IDENTITY_VERSION"], source_system,
                               source_table, source_id, model_key, path, instance["instance_key"])


def _metadata_payload(path, payload, node_uuid, context):
    if context["compiled_plan"]["elements"][path]["parameters"].get("include_uuid"):
        if payload.get("uuid") not in (None, "", node_uuid):
            raise ValueError("Payload UUID conflicts with node UUID")
        return dict(payload, uuid=node_uuid)
    return payload


def _metadata_record_complete(nodes_by_path, context):
    # Linked collections were built together from the same role/party sets.
    context.pop("_metadata_reference_cache", None)


def _element_type(path):
    return path.rsplit(".", 1)[-1].replace("[]", "")


def _canonical_registry_rows(element_registry_df, model_key, context):
    rows = []
    for row in context["registry_rows"]:
        path = _registry_path(row)
        rows.append({"element_path": path, "element_type": row.get("ELEMENT_TYPE") or _element_type(path),
                     "parent_path": row.get("PARENT_NODE_PATH") or None, "level": path.count(".") + 1,
                     "process_order": row.get("PROCESS_ORDER"), "is_collection": _registry_meta_bool(row, "IS_COLLECTION")})
    return sorted(rows, key=lambda row: (row["level"], row["process_order"] if row["process_order"] is not None else 0,
                                         row["element_path"]))


def _metadata_parse(record, context):
    value, options = _to_python(record["CURATED_JSON"]), context["compiled_plan"].get("options", {})
    if context.get("reconcile_property_fields") and value is None:
        raise ValueError("STABLE_PROPERTY_REQUIRES_COMPLETE_SOURCE_DOCUMENT")
    if value is None and options.get("null_source_as_empty", False):
        return {}
    if isinstance(value, str):
        value = json.loads(value, parse_float=Decimal) if options.get("parse_decimal", True) else json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("Source JSON must resolve to an object")
    if context.get("reconcile_property_fields") and not value:
        raise ValueError("STABLE_PROPERTY_REQUIRES_COMPLETE_SOURCE_DOCUMENT")
    return value


def _prepare_model_context(context, model_key, source_system, source_table):
    if context["compiled_plan"].get("release") not in {"lean-csv-registry-v18-native-catalog-bulk", "lean-inline-links-v1"}:
        raise ValueError("Run the matching lean Cell 3 before building the graph")
    config = context["config"]
    config["LINEAGE_GAP_COUNT"] = 0
    if (config["OSCAL_MODEL"], config["SOURCE_SYSTEM_NAME"], config["SOURCE_TABLE_NAME"]) != (model_key, source_system, source_table):
        raise ValueError("Graph arguments conflict with compiled metadata context")
    context.pop("_metadata_reference_cache", None)
    context.pop("_resource_instances", None)
    context["graph_report"] = {"SOURCE_RECORDS": 0, "INVALID_SOURCE_RECORDS": 0, "DUPLICATE_SOURCE_RECORDS": 0,
                               "MAPPED_VALUES": 0, "MISSING_VALUES": 0, "STATUS": "NOT_RUN", "OUTPUTS_PUBLISHED": False,
                               "LINEAGE_PROPS": 0, "LINEAGE_GAPS": 0, "LINEAGE_GAP_SAMPLES": [],
                               "DIRECT_NATIVE_NULL_POLICY": "source-only"}
    return context


def _metadata_prepare(source_df, context):
    if context["route"].get("property_identity") and context["route"]["property_identity"].get("version") != "singleton-properties-v1":
        lifecycle=copy.deepcopy(context["route"]["property_identity"])
        lifecycle["source_key"]=context["source_key"]
        lifecycle["scope"]={k:context["config"][k] for k in ("SOURCE_SYSTEM_NAME","SOURCE_TABLE_NAME","RAW_TABLE","IDENTITY_VERSION","ROOT_PATH","ROOT_ELEMENT_TYPE","TARGET_DIM","TARGET_FACT","DIM_PK_COLUMN","FACT_PK_COLUMN","OSCAL_MODEL")}
        context["config"]["SOURCE_PROPERTY_LIFECYCLE_SPEC"]=lifecycle
        if getattr(globals().get("validate_and_load_oscal"), "_source_property_lifecycle_version", None) != _SOURCE_PROPERTY_LIFECYCLE_VERSION:
            raise ValueError("SOURCE_PROPERTY_LIFECYCLE_MATCHED_LOADER_REQUIRED")
    plan = context["compiled_plan"]
    context["_owner_procedure_bindings"] = _owner_procedure_guid_bindings(context)
    _source_property_complete_prepare(context)
    _stable_property_prepare(context)
    references = [row for row in plan["mappings"] if row["TRANSFORM_ID"] != "skip"
                  and plan["elements"][row["OWNER_ELEMENT_PATH"]]["operator"] == "references"]
    joined_records = [row for row in plan["mappings"] if row["TRANSFORM_ID"] != "skip"
                       and row["REPRESENTATION"] == "joined-records"]
    context["component_hydration_lookups"] = _build_component_hydration_lookups(
        source_df, references, context["lookups"].get("component_sources", {}), context) if references else {}
    extra_fields, title_rows = {}, {}
    for row in plan["mappings"]:
        params = _metadata_params(row)
        if row["TRANSFORM_ID"] == "resource-base64" and params.get("joined_lookup"):
            extra_fields.setdefault(params["joined_lookup"], set()).add(row["SOURCE_FIELD_NAME"])
        elif row["TRANSFORM_ID"] == "resource-citation":
            binding = params["resource_lookup"]
            titles = [item for item in joined_records if _metadata_params(item).get("joined_lookup") == binding
                      and _metadata_target(item) == "title"]
            if len(titles) != 1:
                raise ValueError("Resource citation requires exactly one existing mapped target title")
            title_rows[binding] = titles[0]
    context["_resource_title_rows"] = title_rows
    context["joined_record_lookups"] = _build_joined_record_lookups(
        source_df, joined_records, context, extra_fields=extra_fields) if joined_records else {}
    if extra_fields and not joined_records:
        raise ValueError("Resource field requires its existing compiled joined owner")


def _metadata_finish(nodes, edges, context):
    report = context["graph_report"]
    if not report["SOURCE_RECORDS"] or report["INVALID_SOURCE_RECORDS"] or report["DUPLICATE_SOURCE_RECORDS"]:
        report["STATUS"] = "BLOCKED"
        raise ValueError("Source is empty or contains invalid or duplicate record identities")
    report.update(STATUS="MAPPED_SCOPE_BUILT", OUTPUTS_PUBLISHED=True, NODES=len(nodes), EDGES=len(edges),
                  DOCUMENTS=report["SOURCE_RECORDS"], FULL_MODEL_COMPLETE=False, SCHEMA_VALIDATED=False,
                  LINEAGE_COMPLETE=report["LINEAGE_GAPS"] == 0)



from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote
import unicodedata

CATALOG_PATHS = (
    "catalog",
    "catalog.groups[]",
    "catalog.groups[].groups[]",
    "catalog.groups[].groups[].groups[]",
)
CONTROL_PATHS = tuple(path + ".controls[]" for path in CATALOG_PATHS)
_MISSING = object()


class CatalogControlError(ValueError):
    """Constant reason codes deliberately exclude confidential field values."""


@dataclass(frozen=True)
class ControlFields:
    reference: str
    identifier: str
    title: str
    statement: str

    def validate(self) -> None:
        if not all(isinstance(v, str) and v and v == v.strip()
                   for v in (self.reference, self.identifier, self.title, self.statement)):
            raise CatalogControlError("INVALID_CONTROL_FIELD_CONTRACT")


@dataclass(frozen=True)
class Owner:
    key: str                         # existing DIM candidate node key
    catalog_key: str                 # existing root node key
    parent_key: str | None           # existing CONTAINS parent
    element_path: str
    instance_key: str                # actual current registry instance identity
    source_record_id: str            # original Archer row at this hierarchy level
    existing_ids: tuple[str, ...] = ()  # native group/part IDs, not property values


@dataclass(frozen=True)
class Placement:
    catalog_key: str
    target_source_record_id: str
    owner_key: str
    owner_path: str
    owner_instance_key: str
    control_path: str
    payload: dict[str, Any]
    origin_keys: tuple[str, ...]


@dataclass(frozen=True)
class BulkResult:
    definitions: tuple[Placement, ...]
    group_links: dict[str, tuple[dict[str, str], ...]]
    counts: dict[str, int]


def _source_id(value: Any) -> str:
    if type(value) is int and value > 0:
        return str(value)
    if (isinstance(value, str) and value.isascii() and value.isdecimal()
            and value == str(int(value)) and int(value) > 0):
        return value
    raise CatalogControlError("INVALID_ARCHER_CONTENT_ID")


def _token(value: Any) -> str:
    if not _is_oscal_token(value):
        raise CatalogControlError("NORMALIZER_RETURNED_INVALID_TOKEN")
    return value

def _text(value: Any, required: bool, reason: str) -> str | None:
    if value is _MISSING or value is None or isinstance(value, str) and not value.strip():
        if required:
            raise CatalogControlError(reason)
        return None
    if not isinstance(value, str):
        raise CatalogControlError(reason)
    return value                       # never rewrite the approved title or prose


def build_bulk_catalog_controls(
    owner_rows: Iterable[Owner],
    reference_rows: Iterable[tuple[str, Mapping[str, Any]]],
    target_rows: Iterable[tuple[Any, Mapping[str, Any]]],
    fields: ControlFields,
    normalize_identifier: Callable[[str], str],
    *, promote_mixed_group_controls_to_root: bool = True, target_level_id=None,
    identifier_assignments=None,
) -> BulkResult:
    """Resolve all four owner levels as one deterministic, fail-closed batch.

    reference_rows contains exactly one FULL frozen source document per owner.
    Only fields.reference is read; descendant rollups and underscore variants
    are ignored. Target rows are frozen original Control Standards, keyed by
    CONTENT_ID, not an application field in CURATED_JSON. Inputs are not mutated.
    """
    fields.validate()
    if target_level_id is not None and (type(target_level_id) is not int or target_level_id <= 0):
        raise CatalogControlError("NATIVE_REFERENCE_TARGET_LEVEL_INVALID")
    if type(promote_mixed_group_controls_to_root) is not bool:
        raise CatalogControlError("PLACEMENT_POLICY_MUST_BE_BOOLEAN")
    owners: dict[str, Owner] = {}
    for owner in owner_rows:
        if not isinstance(owner, Owner) or owner.key in owners:
            raise CatalogControlError("DUPLICATE_OR_INVALID_OWNER")
        if (not owner.key or owner.element_path not in CATALOG_PATHS
                or not owner.instance_key or not owner.catalog_key):
            raise CatalogControlError("INVALID_OWNER_CONTRACT")
        _source_id(owner.source_record_id)
        owners[owner.key] = owner
    if not owners:
        raise CatalogControlError("NO_CATALOG_OWNERS")

    ancestry: dict[str, tuple[str, ...]] = {}
    used_ids: dict[str, set[str]] = defaultdict(set)
    for owner in owners.values():
        chain, seen, cursor = [], set(), owner
        while cursor is not None:
            if cursor.key in seen:
                raise CatalogControlError("CYCLIC_OWNER_GRAPH")
            seen.add(cursor.key)
            if cursor.catalog_key != owner.catalog_key:
                raise CatalogControlError("CROSS_CATALOG_PARENT")
            chain.append(cursor.key)
            depth = CATALOG_PATHS.index(cursor.element_path)
            if depth == 0:
                if cursor.parent_key is not None or cursor.key != owner.catalog_key:
                    raise CatalogControlError("INVALID_CATALOG_ROOT")
                break
            parent = owners.get(cursor.parent_key)
            if parent is None or parent.element_path != CATALOG_PATHS[depth - 1]:
                raise CatalogControlError("MISSING_OR_WRONG_OWNER_PARENT")
            cursor = parent
        if not chain or chain[-1] != owner.catalog_key:
            raise CatalogControlError("MISSING_CATALOG_ROOT")
        ancestry[owner.key] = tuple(reversed(chain))
        for identifier in owner.existing_ids:
            if not isinstance(identifier, str) or not identifier:
                raise CatalogControlError("INVALID_EXISTING_NATIVE_ID")
            if identifier in used_ids[owner.catalog_key]:
                raise CatalogControlError("EXISTING_CATALOG_NATIVE_ID_COLLISION")
            used_ids[owner.catalog_key].add(identifier)

    origins: dict[tuple[str, str], set[str]] = defaultdict(set)
    seen_sources, occurrence_count, unique_owner_refs = set(), 0, 0
    for owner_key, document in reference_rows:
        if owner_key not in owners or owner_key in seen_sources or not isinstance(document, Mapping):
            raise CatalogControlError("REFERENCE_OWNER_COVERAGE_OR_SHAPE")
        seen_sources.add(owner_key)
        value = document.get(fields.reference)
        if value is None:
            continue
        if not isinstance(value, list):
            raise CatalogControlError("DIRECT_REFERENCES_MUST_BE_INTEGER_ARRAY")
        owner = owners[owner_key]
        distinct = set()
        for item in value:
            if isinstance(item, dict):
                if target_level_id is None:
                    raise CatalogControlError("DIRECT_REFERENCE_PAIR_REQUIRES_TARGET_LEVEL")
                if set(item) != {"ContentId", "LevelId"}:
                    raise CatalogControlError("DIRECT_REFERENCE_PAIR_KEYS_INVALID")
                if any(type(item[k]) is not int or item[k] <= 0 for k in ("ContentId", "LevelId")):
                    raise CatalogControlError("DIRECT_REFERENCE_PAIR_VALUES_NOT_POSITIVE_INTEGER")
                if item["LevelId"] != target_level_id:
                    raise CatalogControlError("DIRECT_REFERENCE_PAIR_TARGET_LEVEL_MISMATCH")
                item = item["ContentId"]
            if type(item) is not int or item <= 0:  # bool, float, string, object invalid
                raise CatalogControlError("DIRECT_REFERENCE_ITEM_NOT_POSITIVE_INTEGER")
            occurrence_count += 1
            distinct.add(str(item))
        unique_owner_refs += len(distinct)
        for target_id in distinct:
            origins[(owner.catalog_key, target_id)].add(owner_key)
    if seen_sources != owners.keys():
        raise CatalogControlError("MISSING_FROZEN_SOURCE_FOR_OWNER")

    needed = {target for _, target in origins}
    targets: dict[str, Mapping[str, Any]] = {}
    for source_id, payload in target_rows:
        source_id = _source_id(source_id)
        if source_id not in needed:
            continue
        if source_id in targets or not isinstance(payload, Mapping):
            raise CatalogControlError("DUPLICATE_OR_INVALID_REFERENCED_TARGET")
        targets[source_id] = payload
    if targets.keys() != needed:
        raise CatalogControlError("UNRESOLVED_CONTROL_REFERENCE")

    placements, links = [], defaultdict(dict)
    missing_statement = 0
    promoted_mixed_owners = 0
    group_parents = {owner.parent_key for owner in owners.values() if owner.parent_key is not None}
    for (catalog, target_id), origin_set in sorted(origins.items()):
        data = targets[target_id]
        source_name = _text(data.get(fields.identifier, _MISSING), True, "MISSING_CONTROL_ID_SOURCE")
        title = _text(data.get(fields.title, _MISSING), True, "MISSING_CONTROL_TITLE")
        assigned = (identifier_assignments or {}).get((catalog, target_id))
        identifier = _token(assigned if assigned is not None else normalize_identifier(source_name))
        if identifier in used_ids[catalog]:
            raise CatalogControlError("CONTROL_OR_GROUP_ID_COLLISION_AFTER_NORMALIZATION")
        used_ids[catalog].add(identifier)
        chains = [ancestry[origin] for origin in sorted(origin_set)]
        common = []
        for positions in zip(*chains):
            if len(set(positions)) != 1:
                break
            common.append(positions[0])
        if not common:
            raise CatalogControlError("NO_COMMON_OWNER_IN_CATALOG")
        parent = owners[common[-1]]
        # OSCAL 1.2.3 group model chooses nested groups OR controls. The
        # Catalog root may contain both. The owner approved root promotion
        # after that constraint was confirmed against the 1.2.3 metaschema.
        # Links retain associations, NOT inherited group-property semantics.
        if parent.element_path != "catalog" and parent.key in group_parents:
            if not promote_mixed_group_controls_to_root:
                raise CatalogControlError("LCA_GROUP_ALREADY_CONTAINS_GROUPS_POLICY_REVIEW")
            parent = owners[catalog]
            promoted_mixed_owners += 1
        payload = {"id": identifier, "title": title,
                   "props": [{"name": "archer-content-id", "value": target_id}]}
        statement = _text(data.get(fields.statement, _MISSING), False, "INVALID_CONTROL_STATEMENT")
        if statement is not None:
            payload["parts"] = [{"name": "statement", "prose": statement}]
        else:
            missing_statement += 1
        placements.append(Placement(catalog, target_id, parent.key, parent.element_path,
                                    parent.instance_key, parent.element_path + ".controls[]",
                                    payload, tuple(sorted(origin_set))))
        # Source root has no native links member. Root direct ownership is
        # represented by root controls[]; preserve every originating GROUP link.
        for origin in sorted(origin_set):
            if owners[origin].element_path != "catalog":
                href = "#" + quote(identifier, safe="-._~")
                links[origin][href] = {"href": href, "rel": "related"}
    return BulkResult(
        tuple(placements),
        {key: tuple(items[href] for href in sorted(items)) for key, items in sorted(links.items())},
        {"direct_reference_occurrences": occurrence_count,
         "distinct_owner_control_references": unique_owner_refs,
         "referenced_target_records": len(needed),
         "catalog_control_definitions": len(placements),
         "missing_statement_definitions": missing_statement,
         "group_reference_links": sum(len(items) for items in links.values()),
         "schema_compatible_root_promotions": promoted_mixed_owners},
    )


def attach_bulk_result_to_candidate(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], result: BulkResult,
    config: Mapping[str, Any], registered_control_paths: set[str],
    hash_key: Callable[..., str], uuid_key: Callable[..., str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Append to the EXISTING Cell 5 in-memory graph, never write a warehouse.

    Native control identity is per-Catalog + original target ContentId, not the
    changing LCA. Its CONTAINS edge identity is per child, allowing a reparent to
    update an existing edge. Existing group/control-free identities are untouched.
    Deletions still pass through the existing loader's obsolete-row safeguards.
    """
    import json
    if config.get("OSCAL_MODEL") != "CATALOG" or config.get("EXECUTE_WRITES") is not False:
        raise CatalogControlError("CANDIDATE_ONLY_CATALOG_CONTEXT_REQUIRED")
    if (not registered_control_paths or not registered_control_paths.issubset(set(CONTROL_PATHS))
            or "catalog.controls[]" not in registered_control_paths
            or any(p != "catalog.controls[]" and p.rsplit(".groups[]", 1)[0] + ".controls[]" not in registered_control_paths for p in registered_control_paths)):
        raise CatalogControlError("FOUR_CONTROL_REGISTRY_PATHS_REQUIRED")
    node_map = {n["NODE_KEY"]: n for n in nodes}
    if len(node_map) != len(nodes) or any(n["ELEMENT_PATH"] in CONTROL_PATHS for n in nodes):
        raise CatalogControlError("EXPECTED_CONTROL_FREE_BASE_CANDIDATE")
    edge_keys = {e["EDGE_KEY"] for e in edges}
    if len(edge_keys) != len(edges):
        raise CatalogControlError("DUPLICATE_BASE_EDGE")
    output_nodes, output_edges = deepcopy(nodes), deepcopy(edges)
    output_map = {n["NODE_KEY"]: n for n in output_nodes}
    for placement in result.definitions:
        if (placement.control_path != placement.owner_path + ".controls[]" or placement.control_path not in registered_control_paths):
            raise CatalogControlError("UNREGISTERED_CONTROL_PLACEMENT")
        parent = node_map.get(placement.owner_key)
        root = node_map.get(placement.catalog_key)
        if (parent is None or root is None or root["ELEMENT_PATH"] != "catalog"
                or parent["SOURCE_RECORD_ID"] != root["SOURCE_RECORD_ID"]
                or parent["ELEMENT_PATH"] != placement.owner_path
                or parent["INSTANCE_KEY"] != placement.owner_instance_key):
            raise CatalogControlError("PLACEMENT_DOES_NOT_MATCH_CANDIDATE_PARENT")
        seed = (config["IDENTITY_VERSION"], config["SOURCE_SYSTEM_NAME"],
                config["SOURCE_TABLE_NAME"], root["SOURCE_RECORD_ID"], "CATALOG",
                "catalog.controls[]", placement.target_source_record_id)
        key, uuid = hash_key(*seed), uuid_key(*seed)
        if key in output_map:
            raise CatalogControlError("CONTROL_NODE_HASH_COLLISION")
        # Copy audit/source-column conventions from the same Catalog's root.
        node = dict(root, NODE_KEY=key, ELEMENT_PATH=placement.control_path,
                    PARENT_NODE_PATH=placement.owner_path,
                    INSTANCE_KEY=placement.target_source_record_id,
                    PARENT_INSTANCE_KEY=parent["INSTANCE_KEY"], OSCAL_UUID=uuid,
                    ELEMENT_TYPE="controls",
                    METADATA_JSON=json.dumps(placement.payload, sort_keys=True,
                                             ensure_ascii=False, allow_nan=False))
        edge_key = hash_key("catalog-control-owner-edge-v1", key, "CONTAINS")
        if edge_key in edge_keys:
            raise CatalogControlError("CONTROL_EDGE_HASH_COLLISION")
        edge_keys.add(edge_key)
        output_nodes.append(node)
        output_map[key] = node
        output_edges.append({"EDGE_KEY": edge_key,
                             "FK_SOURCE_ELEMENT_HASH": parent["NODE_KEY"],
                             "FK_TARGET_ELEMENT_HASH": key, "DEPENDENCY_TYPE": "CONTAINS",
                             "SOURCE_OSCAL_UUID": parent["OSCAL_UUID"], "TARGET_OSCAL_UUID": uuid})
    for owner, additions in result.group_links.items():
        node = output_map.get(owner)
        if node is None or node["ELEMENT_PATH"] not in CATALOG_PATHS[1:]:
            raise CatalogControlError("GROUP_LINK_OWNER_MISSING")
        payload = json.loads(node["METADATA_JSON"])
        existing = payload.setdefault("links", [])
        if not isinstance(existing, list) or any(not isinstance(x, dict) for x in existing):
            raise CatalogControlError("INVALID_EXISTING_GROUP_LINKS")
        pairs = {(x.get("href"), x.get("rel")) for x in existing}
        for link in additions:
            if (link["href"], link["rel"]) not in pairs:
                existing.append(dict(link))
                pairs.add((link["href"], link["rel"]))
        node["METADATA_JSON"] = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return output_nodes, output_edges

# Reused from the reviewed pure Procedure-property contract; no runtime imports.
from uuid import UUID

class ProcedureReferenceContractError(ValueError):
    """Fail-closed mapping-contract exception without leaking source values."""


def _procedure_property_identity(source_field_guid, namespace_mode, property_name):
    """Owner-approved constant name and machine GUID-derived namespace only."""
    if namespace_mode != "archer-field-guid-urn" or property_name != "procedure-reference":
        raise ProcedureReferenceContractError("APPROVED_GUID_URN_PROPERTY_IDENTITY_REQUIRED")
    return property_name, UUID(_field_guid(source_field_guid)).urn


def _field_guid(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProcedureReferenceContractError("ARCHER_FIELD_GUID_REQUIRED")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ProcedureReferenceContractError("INVALID_ARCHER_FIELD_GUID") from exc
    # Do not silently normalize the real metadata field GUID.
    if str(parsed).lower() != value.lower():
        raise ProcedureReferenceContractError("NONCANONICAL_ARCHER_FIELD_GUID")
    return value


def _procedure_ids(raw: object) -> list[str]:
    raw = _restore_inline_reference_value(raw)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ProcedureReferenceContractError("PROCEDURE_REFERENCES_MUST_BE_ARRAY")
    found: set[int] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ProcedureReferenceContractError("PROCEDURE_REFERENCE_NOT_OBJECT")
        pid, level = item.get("ContentId"), item.get("LevelId")
        if type(pid) is not int or pid <= 0:
            raise ProcedureReferenceContractError("INVALID_PROCEDURE_CONTENT_ID")
        if type(level) is not int or level != 39:
            raise ProcedureReferenceContractError("WRONG_PROCEDURE_LEVEL_ID")
        found.add(pid)
    return [str(identifier) for identifier in sorted(found)]


def preview_guid_named_procedure_props(
    *, source_field_guid: str, namespace_mode: str, property_name: str,
    raw_procedure_references: object,
) -> list[dict[str, str]]:
    """Propose one real-source-ID STRING prop per unique referenced Procedure.

    Must be called for the EXACT owning source field/node. This function never
    resolves owner-grain refs through Control Standards or derives a Control
    Procedure URL. Distinct owner and Standard relationships stay distinct.
    """
    name, ns = _procedure_property_identity(source_field_guid, namespace_mode, property_name)
    return [{"name": name, "ns": ns, "value": pid}
            for pid in _procedure_ids(raw_procedure_references)]


def preview_merge_on_existing_owner(
    existing_payload: dict, *, source_field_guid: str,
    namespace_mode: str, property_name: str, raw_procedure_references: object,
) -> dict:
    """Preview SCD1-style replacement without touching identity or other props."""
    if not isinstance(existing_payload, dict):
        raise ProcedureReferenceContractError("EXISTING_OSCAL_PAYLOAD_NOT_OBJECT")
    result = deepcopy(existing_payload)
    original = result.get("props", [])
    if not isinstance(original, list) or any(not isinstance(p, dict) for p in original):
        raise ProcedureReferenceContractError("EXISTING_OSCAL_PROPS_INVALID")
    proposed = preview_guid_named_procedure_props(
        source_field_guid=source_field_guid,
        namespace_mode=namespace_mode, property_name=property_name,
        raw_procedure_references=raw_procedure_references,
    )
    key = _procedure_property_identity(source_field_guid, namespace_mode, property_name)
    kept = [p for p in original if (p.get("name"), p.get("ns")) != key]
    # An explicit empty source list replaces stale owned reference props.
    # Unrelated old props and node id/title/parts remain unchanged.
    updated_props = kept + proposed
    if updated_props:
        result["props"] = updated_props
    else:
        result.pop("props", None)  # OSCAL arrays should not be left empty
    return result


def _native_catalog_guid_binding(lookups, spec):
    """Validate the same frozen machine metadata used by this compiled opt-in."""
    contract = spec.get("guid_props")
    if contract is None:
        return None
    binding = spec["lookup"]
    if lookups.get("native_control_guid_contract", {}).get(binding) != contract:
        raise ProcedureReferenceContractError("FIELD_GUID_METADATA_CONTRACT_DRIFT")
    frame = lookups.get("native_control_guid_metadata", {}).get(binding)
    if frame is None:
        raise ProcedureReferenceContractError("FIELD_GUID_METADATA_SNAPSHOT_REQUIRED")
    rows = []
    for raw in frame.to_local_iterator():
        record = raw.as_dict(recursive=True) if hasattr(raw, "as_dict") else dict(raw)
        if not {"LEVEL_ID", "FIELD_ID", "FIELD_GUID", "SQL_FIELD_NAME"}.issubset(record):
            raise ProcedureReferenceContractError("FIELD_GUID_METADATA_COLUMNS_REQUIRED")
        rows.append(record)
    def metadata_id(value):
        if type(value) is int:
            return value
        if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
            return int(value)
        return None
    matched = [row for row in rows
               if metadata_id(row["LEVEL_ID"]) == contract["level_id"]
               and metadata_id(row["FIELD_ID"]) == contract["field_id"]]
    if len(matched) != 1:
        raise ProcedureReferenceContractError("EXACT_FIELD_GUID_METADATA_ROW_REQUIRED")
    actual = matched[0]
    if actual["SQL_FIELD_NAME"] != contract["source_field"]:
        raise ProcedureReferenceContractError("FIELD_GUID_SOURCE_FIELD_MISMATCH")
    field_guid = _field_guid(actual["FIELD_GUID"])
    canonical_guid = str(UUID(field_guid))
    count = 0
    for row in rows:
        try:
            candidate = str(UUID(row["FIELD_GUID"]))
        except (TypeError, ValueError, AttributeError):
            continue
        count += candidate == canonical_guid
    if count != 1:
        raise ProcedureReferenceContractError("FIELD_GUID_METADATA_NOT_UNIQUE")
    property_name, namespace = _procedure_property_identity(
        field_guid, contract["namespace_mode"], contract["property_name"])
    return {"field_guid": field_guid, "namespace": namespace,
            "namespace_mode": contract["namespace_mode"], "property_name": property_name,
            "source_field": contract["source_field"]}



def _owner_procedure_guid_bindings(context):
    spec = context["compiled_plan"].get("owner_procedure_props")
    if spec is None:return {}
    frames = context["lookups"].get("owner_procedure_guid_metadata", {})
    result = {}
    for key,d in spec["contracts"].items():
        frame = frames.get(d.get("metadata_binding", key))
        if frame is None:raise ProcedureReferenceContractError("EXACT_OWNER_FIELD_LOOKUP_FRAME_REQUIRED")
        result[key] = _resolve_guid_from_frame(frame,d)
    return result



def _owner_procedure_binding(row, context):
    key = _owner_procedure_key(row["OWNER_ELEMENT_PATH"],row["SOURCE_FIELD_NAME"],_metadata_params(row).get("joined_lookup"))
    binding = context.get("_owner_procedure_bindings", {}).get(key)
    if binding is None or _metadata_params(row).get("owner_procedure_binding") != key or binding["source_field"] != row["SOURCE_FIELD_NAME"] or row["TRANSFORM_ID"] != "catalog-owner-procedure-props":raise ProcedureReferenceContractError("EXACT_OWNER_PROCEDURE_BINDING_REQUIRED")
    return binding



def _validate_joined_property_collisions(props, path, context):
    props = _scalar_array_joined_legacy_props(props,path,context)
    declarations = context["compiled_plan"].get("owner_procedure_props") or {}
    approved = set()
    for key,d in declarations.get("contracts",{}).items():
        if d["owner_path"] == path:
            b=context["_owner_procedure_bindings"][key];token=(b["property_name"],b["namespace"])
            if token in approved:raise ProcedureReferenceContractError("AMBIGUOUS_OWNER_PROPERTY_NAMESPACE")
            approved.add(token)
    legacy, seen = [], set()
    for prop in props:
        token=(prop.get("name"),prop.get("ns"))
        if token not in approved:legacy.append(token);continue
        if set(prop)!={"name","ns","value"} or any(not isinstance(prop[k],str) for k in prop):raise ProcedureReferenceContractError("INVALID_OWNER_PROCEDURE_PROPERTY")
        identity=token+(prop["value"],)
        if identity in seen:raise ProcedureReferenceContractError("DUPLICATE_OWNER_PROCEDURE_REFERENCE")
        seen.add(identity)
    if len(legacy)!=len(set(legacy)):raise ValueError("Joined child property names collide")



def _native_catalog_identifier_assignments(context, roots):
    """Explicit route/owner/target assignments; no guessed identity or target reads."""
    name = "NATIVE_CATALOG_ID_ASSIGNMENTS"
    config = context["config"]
    declaration = config.get(name)
    if declaration is None:
        authority = globals().get("_ROUTE_AUTHORITY") or {}
        frozen = authority.get((config.get("SOURCE_KEY"), config.get("OSCAL_MODEL")))
        if (context["route"].get("constant_values", {}).get(name) is not None
                or frozen and json.loads(frozen).get("constant_values", {}).get(name) is not None):
            raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENTS_CONFIG_MISSING")
        return {}
    key = (config.get("SOURCE_KEY"), config.get("OSCAL_MODEL"))
    frozen = globals().get("_ROUTE_AUTHORITY")
    if (key[1] != "CATALOG" or not frozen or key not in frozen
            or json.loads(frozen[key]).get("constant_values", {}).get(name) != declaration
            or context["route"].get("constant_values", {}).get(name) != declaration):
        raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENTS_AUTHORITY_MISMATCH")
    if (type(declaration) is not dict or set(declaration) != {"version", "assignments"}
            or declaration["version"] != "owner-target-native-id-v1"
            or type(declaration["assignments"]) is not list or not declaration["assignments"]):
        raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENTS_INVALID")
    result, pairs, tokens = {}, set(), set()
    for item in declaration["assignments"]:
        if type(item) is not dict or set(item) != {"owner_content_id", "target_content_id", "oscal_id"}:
            raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENT_FIELDS_INVALID")
        owner, target, token = item["owner_content_id"], item["target_content_id"], item["oscal_id"]
        if (type(owner) is not str or type(target) is not str
                or _source_id(owner) != owner or _source_id(target) != target or not _is_oscal_token(token)):
            raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENT_ID_INVALID")
        if (owner, target) in pairs or (owner, token) in tokens:
            raise ValueError("NATIVE_CATALOG_ID_ASSIGNMENT_DUPLICATED")
        pairs.add((owner, target)); tokens.add((owner, token))
        if owner in roots:
            result[(roots[owner]["NODE_KEY"], target)] = token
    plan = context["compiled_plan"]
    base = context.setdefault("native_catalog_assignment_base_fingerprint", plan["mapping_fingerprint"])
    plan["mapping_fingerprint"] = hashlib.sha256(json.dumps(
        [base, declaration], sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    context["graph_report"]["NATIVE_CATALOG_ID_ASSIGNMENT_POLICY"] = declaration["version"]
    return result


def _native_catalog_timestamp(value):
    """Normalize a date or an explicitly zoned timestamp without losing precision."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
        r"(?:[Tt ](?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
        r"(?P<fraction>\.[0-9]{1,9})?(?P<zone>[Zz]|[+-][0-9]{2}:?[0-9]{2}))?",
        value.strip(),
    )
    if match is None:
        return None
    date = match["date"]
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return None
    zone = match["zone"]
    if zone is None:
        return date
    hour, minute, second = (match[part] for part in ("hour", "minute", "second"))
    if int(hour) > 23 or int(minute) > 59 or int(second) > 59:
        return None
    if zone.upper() == "Z":
        zone = "Z"
    else:
        if int(zone[1:3]) > 23 or int(zone[-2:]) > 59:
            return None
        zone = f"{zone[:3]}:{zone[-2:]}"
    return f"{date}T{hour}:{minute}:{second}{match['fraction'] or ''}{zone}"


def _native_catalog_apply(nodes, edges, source_df, context):
    """One bulk candidate-stage operation. No writer, SQL, or model fan-out."""
    spec = context["compiled_plan"].get("native_catalog")
    if spec is None:
        return nodes, edges
    families = None
    if spec.get("plan_capability") == "native-catalog-reference-families-v1":
        families = spec["families"]
        if not isinstance(families,list) or len(families)<2:
            raise ValueError("Native Catalog reference family plan invalid")
        spec = families[0]
    if "plan_capability" in spec:
        if spec["plan_capability"] != "native-catalog-selected-owners-v1" or "owner_bindings" in spec:
            raise ValueError("Unsupported native Catalog selected-owner protocol")
        spec = dict(spec, owner_bindings=spec["declared_owner_bindings"])
    config = context["config"]
    if config["OSCAL_MODEL"] != "CATALOG" or config["EXECUTE_WRITES"] is not False:
        raise ValueError("Native Catalog requires a no-write candidate context")
    config["NATIVE_CATALOG_EDGE_POLICY"] = "catalog-control-owner-edge-v1"
    lookups = context["lookups"]
    target_frame = lookups.get("native_control_sources", {}).get(spec["lookup"])
    if target_frame is None:
        raise ValueError("Native Catalog frozen Control Standards lookup is missing; rerun matching Cell 2")
    roots = {n["SOURCE_RECORD_ID"]: n for n in nodes if n["ELEMENT_PATH"] == "catalog"}
    identifier_assignments = _native_catalog_identifier_assignments(context, roots)
    parent_keys = {e["FK_TARGET_ELEMENT_HASH"]: e["FK_SOURCE_ELEMENT_HASH"] for e in edges}
    owner_nodes = [n for n in nodes if n["ELEMENT_PATH"] in spec["owner_bindings"]]
    source_docs = {}
    sources = {None: source_df, **lookups.get("joined_sources", {})}
    reference_field = spec["fields"][""]
    reference_fields = {f["fields"][""] for f in families} if families else {reference_field}
    for path, binding in spec["owner_bindings"].items():
        frame = sources.get(binding)
        if frame is None:
            raise ValueError("Native Catalog frozen owner lookup is missing")
        records = {}
        for record in frame.to_local_iterator():
            identifier = _source_id(record["SOURCE_RECORD_ID" if binding is None else "_SOURCE_RECORD_ID"])
            if identifier in records:
                raise ValueError("Native Catalog source owner identity is duplicated")
            document = _metadata_parse(record, context)
            # Keep exact field spelling. Descendant rollups are deliberately not inputs.
            records[identifier] = {field: _restore_inline_reference_value(document.get(field))
                                   for field in reference_fields}
        source_docs[binding] = records

    def native_ids(payload):
        values = []
        if isinstance(payload.get("id"), str):
            values.append(payload["id"])
        for part in payload.get("parts", ()):
            if not isinstance(part, dict):
                raise ValueError("Existing Catalog part has invalid shape")
            values.extend(native_ids(part))
        return tuple(values)

    owners, references = [], []
    family_occurrences = {family["lookup"]:0 for family in families} if families else None
    family_origins = {}
    for node in owner_nodes:
        root = roots.get(node["SOURCE_RECORD_ID"])
        if root is None:
            raise ValueError("Native Catalog owner root is missing")
        payload = json.loads(node["METADATA_JSON"])
        binding = spec["owner_bindings"][node["ELEMENT_PATH"]]
        if binding is None:
            source_id = node["SOURCE_RECORD_ID"]
        else:
            name = lookups["joined_contract"][binding]["child_record_id_property"]
            ids = [p.get("value") for p in payload.get("props", ()) if p.get("name") == name]
            if len(ids) != 1:
                raise ValueError("Native Catalog group lacks unambiguous Archer provenance")
            source_id = _source_id(ids[0])
        if source_id not in source_docs[binding]:
            raise ValueError("Native Catalog group source record not found in frozen input")
        owners.append(Owner(node["NODE_KEY"], root["NODE_KEY"],
                            parent_keys.get(node["NODE_KEY"]), node["ELEMENT_PATH"],
                            node["INSTANCE_KEY"], source_id, native_ids(payload)))
        if families:
            combined = []
            for family in families:
                family_owners = family.get("declared_owner_bindings", family.get("owner_bindings"))
                if node["ELEMENT_PATH"] not in family.get("reference_owner_paths", family_owners):
                    continue
                values = source_docs[binding][source_id].get(family["fields"][""])
                if values is None:
                    continue
                if not isinstance(values,list):
                    raise ValueError("Native Catalog reference family must be an array")
                family_occurrences[family["lookup"]] += len(values)
                for reference in values:
                    # The bulk validator below checks all reference shapes and levels.
                    target_id = _source_id(reference.get("ContentId") if isinstance(reference,dict) else reference)
                    origin = (family["lookup"],family["fields"][""],node["NODE_KEY"],target_id)
                    family_origins[origin] = family_origins.get(origin,0)+1
                combined.extend(values)
            references.append((node["NODE_KEY"], {reference_field:combined}))
        elif node["ELEMENT_PATH"] in spec.get("reference_owner_paths", spec["owner_bindings"]):
            references.append((node["NODE_KEY"], source_docs[binding][source_id]))
        else:
            references.append((node["NODE_KEY"], {}))

    fields = spec["fields"]
    extra_props = spec.get("extra_props", [])
    guid_binding = _native_catalog_guid_binding(lookups, spec)
    if families and any(_native_catalog_guid_binding(lookups,family) != guid_binding for family in families):
        raise ValueError("Native Catalog reference family GUID metadata conflicts")
    target_field_names = [fields["id"], fields["title"], fields["parts"]]
    if guid_binding:
        target_field_names.append(guid_binding["source_field"])
    target_field_names.extend(prop["source_field"] for prop in extra_props)
    if families:
        # A common physical domain must really be the same frozen snapshot.
        # Compare declared hydration members including missing-versus-null shape.
        snapshots = []
        for family in families:
            frame = lookups.get("native_control_sources",{}).get(family["lookup"])
            if frame is None:raise ValueError("Native Catalog reference family snapshot missing")
            snapshot = {}
            for record in frame.to_local_iterator():
                identifier = _source_id(record["SOURCE_RECORD_ID"])
                if identifier in snapshot:raise ValueError("Native Catalog reference family target identity ambiguous")
                raw = _metadata_parse(record,context)
                snapshot[identifier] = {field:(field in raw,raw.get(field)) for field in target_field_names}
            snapshots.append(snapshot)
        if any(snapshot != snapshots[0] for snapshot in snapshots[1:]):
            raise ValueError("Native Catalog reference family snapshots conflict")
    targets = []
    statement_shapes = {}
    for record in target_frame.to_local_iterator():
        raw_target = _metadata_parse(record, context)
        statement = raw_target.get(fields["parts"])
        statement_shapes[_source_id(record["SOURCE_RECORD_ID"])] = ("MISSING" if fields["parts"] not in raw_target else "NULL" if statement is None else "BLANK" if isinstance(statement, str) and not statement.strip() else "POPULATED")
        targets.append((_source_id(record["SOURCE_RECORD_ID"]),
                        {name: raw_target.get(name) for name in target_field_names}))
    def native_token(value):
        if spec.get("id_policy") == "preserve-valid-token-reject-invalid":
            if not isinstance(value, str) or not _is_oscal_token(value):
                raise ValueError("Native control identifier is not an exact valid OSCAL token")
            return value
        return _oscal_token(value)
    result = build_bulk_catalog_controls(
        owners, references, targets,
        ControlFields(reference_field, fields["id"], fields["title"], fields["parts"]),
        native_token, promote_mixed_group_controls_to_root=True,
        target_level_id=spec.get("target_level_id"), identifier_assignments=identifier_assignments)
    if "NATIVE_CATALOG_ID_ASSIGNMENTS" in config:
        context["graph_report"]["NATIVE_CATALOG_CONTROL_ID_OVERRIDES_APPLIED"] = sum(
            (p.catalog_key, p.target_source_record_id) in identifier_assignments for p in result.definitions)
    if spec.get("plan_capability") == "native-catalog-selected-owners-v1":
        for shape in ("MISSING", "NULL", "BLANK", "POPULATED"):
            context["graph_report"]["NATIVE_CATALOG_STATEMENT_" + shape] = sum(statement_shapes[p.target_source_record_id] == shape for p in result.definitions)
    # Automatic same-snapshot value acceptance is part of the mapper, not a
    # separate user QA cell. Do not claim a populated statement check when absent.
    target_values = dict(targets)
    for placement in result.definitions:
        original = target_values[placement.target_source_record_id]
        expected_id = identifier_assignments.get((placement.catalog_key, placement.target_source_record_id))
        if expected_id is None:
            expected_id = native_token(original[fields["id"]])
        expected_title = original[fields["title"]]
        statement = original[fields["parts"]]
        expected_parts = ([] if statement is None or isinstance(statement, str) and not statement.strip()
                          else [{"name": "statement", "prose": statement}])
        if (placement.payload.get("id") != expected_id
                or placement.payload.get("title") != expected_title
                or placement.payload.get("parts", []) != expected_parts):
            raise ValueError("Native Catalog candidate differs from frozen target fields")
    if guid_binding:
        # Each definition refers to its ORIGINAL Standard ContentId. Do not
        # derive these references from Source/group arrays or inverse fields.
        for placement in result.definitions:
            original = target_values[placement.target_source_record_id]
            updated = preview_merge_on_existing_owner(
                placement.payload, source_field_guid=guid_binding["field_guid"],
                namespace_mode=guid_binding["namespace_mode"],
                property_name=guid_binding["property_name"],
                raw_procedure_references=original.get(guid_binding["source_field"]))
            placement.payload.clear()
            placement.payload.update(updated)
        context["graph_report"]["NATIVE_CATALOG_GUID_PROPS_FIELD_VALUE_CHECK"] = (
            "STANDARD_OWNED_DEDUPLICATED_LEVEL39_REFERENCES")
        context["graph_report"]["NATIVE_CATALOG_GUID_PROP_OCCURRENCES"] = sum(
            sum(prop.get("name") == guid_binding["property_name"]
                and prop.get("ns") == guid_binding["namespace"]
                for prop in placement.payload.get("props", ()))
            for placement in result.definitions)
    if extra_props:
        occurrences = 0
        timestamp_fallbacks = 0
        for placement in result.definitions:
            original = target_values[placement.target_source_record_id]
            props = placement.payload["props"]
            identities = {(prop["name"], prop.get("ns"), prop.get("class")) for prop in props}
            for prop in extra_props:
                value = original.get(prop["source_field"])
                if value is None:
                    continue
                name, namespace = prop["property_name"], prop["namespace"]
                prop_class = prop.get("class")
                identity = (name, namespace, prop_class)
                if identity in identities:
                    raise ValueError("Duplicate native Catalog property identity")
                is_timestamp = prop.get("transform") == "timestamp"
                timestamp = _native_catalog_timestamp(value) if is_timestamp else None
                if is_timestamp and timestamp is None:
                    timestamp_fallbacks += 1
                value_text = timestamp if timestamp is not None else _metadata_json_text(value)
                payload = {"name": name, "ns": namespace, "value": value_text}
                if prop_class is not None:
                    payload["class"] = prop_class
                props.append(payload)
                identities.add(identity)
                occurrences += 1
        context["graph_report"]["NATIVE_CATALOG_EXTRA_PROP_OCCURRENCES"] = occurrences
        if any(prop.get("transform") == "timestamp" for prop in extra_props):
            context["graph_report"]["NATIVE_CATALOG_TIMESTAMP_FALLBACK_OCCURRENCES"] = timestamp_fallbacks
    new_nodes, new_edges = attach_bulk_result_to_candidate(
        nodes, edges, result, config, set(spec["paths"]),
        _deterministic_hash, _deterministic_uuid)
    context["graph_report"].update(
        {"NATIVE_CATALOG_" + key.upper(): value for key, value in result.counts.items()})
    if families:
        context["graph_report"]["NATIVE_CATALOG_REFERENCE_FAMILIES"] = len(families)
        context["graph_report"]["NATIVE_CATALOG_REFERENCE_FAMILY_OCCURRENCES"] = family_occurrences
        owner_by_key = {node["NODE_KEY"]:node for node in owner_nodes}
        controls_by_source = {(node["SOURCE_RECORD_ID"],node["INSTANCE_KEY"]):node["NODE_KEY"]
                              for node in new_nodes if node["ELEMENT_PATH"] in spec["paths"]}
        context["graph_report"]["NATIVE_CATALOG_REFERENCE_CONTRIBUTIONS"] = [
            {"lookup_key":binding,"source_field":field,"owner_node_key":owner,
             "target_node_key":controls_by_source[(owner_by_key[owner]["SOURCE_RECORD_ID"],target)],
             "occurrences":count}
            for (binding,field,owner,target),count in sorted(family_origins.items())]
    context["graph_report"]["NATIVE_CATALOG_FIELD_VALUE_CHECK"] = "CANDIDATE_MATCHES_FROZEN_TARGET_FIELDS"
    context["graph_report"]["NATIVE_CATALOG_FULL_DOCUMENT_CONFORMANCE"] = False
    # _attach_record_lineage() ran before bulk Catalog assembly. Propagate
    # unresolved related-link mapping gaps to the SAME existing COMMIT gate.
    config["LINEAGE_GAP_COUNT"] = context["graph_report"]["LINEAGE_GAPS"]
    pending_reasons = ("SELF_REFERENCE_PENDING", "CROSS_CATALOG_REFERENCE_PENDING",
                       "UNKNOWN_TARGET_REFERENCE_PENDING")
    context["graph_report"]["NATIVE_CATALOG_SUBSECTION_LINK_COVERAGE_COMPLETE"] = (
        not any(context["graph_report"].get("NATIVE_CATALOG_SUBSECTION_" + reason, 0)
                for reason in pending_reasons))
    return new_nodes, new_edges


print("Cell 4 transforms and registry operators ready")

_metadata_instances._oscal_mapper_release = "lean-csv-registry-v18-native-catalog-bulk"

def _resolve_guid_from_frame(frame, contract):
    if frame is None:raise ProcedureReferenceContractError("FIELD_GUID_METADATA_REQUIRED")
    resolved = dict(contract)
    if resolved.get("field_id") is None:
        if not isinstance(resolved.get("metadata_binding"),str) or resolved.get("field_id_resolution") != "unique-level-source-field" or type(resolved.get("level_id")) is not int:raise ProcedureReferenceContractError("EXPLICIT_GUID_DOMAIN_REQUIRED")
        rows = [r.as_dict() if hasattr(r,"as_dict") else dict(r) for r in frame.to_local_iterator()]
        def number(v):
            if type(v) is int:return v
            if isinstance(v,Decimal) and v.is_finite() and v == v.to_integral_value():return int(v)
            return None
        matches = [r for r in rows if number(r.get("LEVEL_ID")) == resolved["level_id"] and r.get("SQL_FIELD_NAME") == resolved["source_field"]]
        if len(matches) != 1 or not number(matches[0].get("FIELD_ID")) or number(matches[0]["FIELD_ID"]) <= 0:raise ProcedureReferenceContractError("EXACT_FIELD_GUID_METADATA_ROW_REQUIRED")
        resolved["field_id"] = number(matches[0]["FIELD_ID"])
    result = _native_catalog_guid_binding({"native_control_guid_metadata":{"explicit":frame},"native_control_guid_contract":{"explicit":resolved}}, {"lookup":"explicit", "guid_props":resolved})
    return dict(result, level_id=resolved["level_id"], field_id=resolved["field_id"])



def _inline_link_instances(source_obj, source_id, rows, parameters, context):
    """Declared inline URL objects; no raw member becomes an undeclared native member."""
    import string
    declaration = parameters["inline_link_contract"]
    result = []
    for row in rows:
        raw = resolve_json_path(source_obj, row["SOURCE_FIELD_NAME"], default=SKIP_VALUE)
        if raw is SKIP_VALUE or raw is None:
            continue
        if not isinstance(raw, list):
            raise ValueError("Inline links require an array")
        declared_keys = {declaration[k] for k in ("id_key", "name_key", "href_key", "order_key")}
        normalized = []
        for member in raw:
            if not isinstance(member, dict) or set(member) != declared_keys:
                raise ValueError("Inline link member does not match declared source keys")
            normalized.append({"Id": member[declaration["id_key"]], "Name": member[declaration["name_key"]],
                               "Url": member[declaration["href_key"]], "SortOrder": member[declaration["order_key"]]})
        try:
            validated = _validated_link_array(normalized)
        except (TypeError, ValueError, ArithmeticError):
            raise ValueError("Malformed inline links for field " + row["SOURCE_FIELD_NAME"]) from None
        for _, identity, label, href, order in validated:
            uri = urlsplit(href)
            if (uri.scheme not in declaration["allowed_schemes"] or uri.username is not None
                    or not href.isascii() or any(ord(c) < 33 or ord(c) == 127 for c in href)
                    or any(c in href for c in '<>"{}|^`\\[]') or href.count('#') > 1
                    or re.search(r"%(?![0-9A-Fa-f]{2})", href)
                    or any(ord(c) < 32 or ord(c) == 127 for c in label)):
                raise ValueError("Inline link requires allowed literal URI and label syntax")
            payload = {"href": href, "rel": declaration["rel"]}
            if declaration["include_text"]:
                payload["text"] = "".join("\\" + c if c in string.punctuation else c for c in label)
            result.append({"instance_key": _deterministic_hash("inline-link-v1", row["SOURCE_FIELD_NAME"], identity),
                           "payload": payload, "contributions": [],
                           "parent_instance_key": _metadata_parent_key(parameters, source_id)})
    return result
