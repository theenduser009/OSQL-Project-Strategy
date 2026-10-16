# %% Source Two CATALOG next-mapping gates — READ ONLY (2026-10-16)
# Run as ONE new Python cell in the existing successful Snowflake DEV notebook.
# Uses retained Cell 2 Source/Topic/Section/Sub-Section CURATED_JSON frames.
# Snowpark issues read-only SELECTs. No registry/target writes, MERGE or COMMIT.
# Prints aggregate counts and JSON FIELD NAMES/TYPES only.
# Never prints Source records, Content IDs, business values, dates, or URLs.

import datetime
import json
import math
import re
from collections import Counter
from decimal import Decimal
from urllib.parse import urlsplit

_FIELDS = {
    "Source": ("DATE_CREATED", "LAST_UPDATED"),
    "Topic": ("TOPIC_DATE_CREATED", "TOPIC_LAST_UPDATED"),
    "Section": ("SUM_OF_SUB_SECTION_CRITICALITY_VALUE",),
    "Sub-Section": ("SUB_SECTION_DATE_CREATED", "SUB_SECTION_LAST_UPDATED"),
}
_TIMESTAMP_FIELDS = {
    field for level, fields in _FIELDS.items()
    for field in fields if field != "SUM_OF_SUB_SECTION_CRITICALITY_VALUE"
}
_URL_KEY_TOKENS = {"url", "uri", "href", "link", "address", "location"}
_MAX_OUTPUT_KEYS = 40
_MISSING = object()


def _profile_json_obj(record):
    value = record["CURATED_JSON"]
    if hasattr(value, "as_dict"):
        value = value.as_dict(recursive=True)
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("Cached CURATED_JSON must be an object")
    return value


def _profile_kind(value):
    if value is None:
        return "JSON_NULL"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, str):
        return "TEXT" if value else "EMPTY_TEXT"
    if isinstance(value, (int, float, Decimal)):
        return "NUMBER"
    if isinstance(value, list):
        return "ARRAY"
    if isinstance(value, dict):
        return "OBJECT"
    return "OTHER"


def _profile_datetime_shape(value):
    if value is _MISSING:
        return "MISSING_KEY", False
    if value is None:
        return "JSON_NULL", False
    if not isinstance(value, str):
        return "NON_TEXT", False
    trim_changed = value != value.strip()
    text = value.strip()
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}"
        r"(?:\.\d{1,9})?(?:[Zz]|[+-]\d{2}:\d{2})?",
        text,
    ):
        return "INVALID_TIMESTAMP_SYNTAX", trim_changed
    try:
        normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
        parsed = datetime.datetime.fromisoformat(normalized)
    except (ValueError, TypeError, OverflowError):
        return "INVALID_TIMESTAMP_DATE", trim_changed
    return (
        "VALID_WITH_TIMEZONE" if parsed.tzinfo is not None else "VALID_NO_TIMEZONE",
        trim_changed,
    )


def _profile_finite_number(value):
    if value is _MISSING:
        return "MISSING_KEY"
    if value is None:
        return "JSON_NULL"
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return "NOT_NUMERIC"
    try:
        if isinstance(value, Decimal):
            finite = value.is_finite()
        elif isinstance(value, float):
            finite = math.isfinite(value)
        else:
            finite = True
    except (TypeError, ValueError):
        finite = False
    return "FINITE_NUMBER" if finite else "NONFINITE_NUMBER"


def _profile_key_summary(counter):
    values = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return {
        "distinct_key_types": len(values),
        "top_keys": [{"key": key, "count": count}
                     for key, count in values[:_MAX_OUTPUT_KEYS]],
        "truncated": len(values) > _MAX_OUTPUT_KEYS,
    }


def _profile_url_scheme(value):
    if not isinstance(value, str) or not value.strip():
        return "NOT_NONEMPTY_TEXT"
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return "INVALID_URI_SYNTAX"
    if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
        return parsed.scheme.lower()
    if parsed.scheme:
        return "OTHER_SCHEME"
    return "RELATIVE_OR_NO_SCHEME"


def run_source_two_next_mapping_detail_gates(namespace=None):
    scope = globals() if namespace is None else namespace
    cached = scope.get("SOURCE_INPUTS", {}).get("source-two-source")
    if not cached:
        raise ValueError("MISSING_CACHED_SOURCE_TWO: do not rerun a completed COMMIT")
    joined = cached.get("lookups", {}).get("joined_sources", {})
    frames = {
        "Source": cached.get("source_df"),
        "Topic": joined.get("topics"),
        "Section": joined.get("sections"),
        "Sub-Section": joined.get("subsections"),
    }
    if any(frame is None or not hasattr(frame, "to_local_iterator")
           for frame in frames.values()):
        raise ValueError("MISSING_FOUR_LEVEL_CACHED_FRAMES: no source reload performed")
    result = {
        "status": "READ_ONLY_SOURCE_TWO_NEXT_MAPPING_DETAIL_GATES",
        "writes_executed": False,
        "fields": [],
    }
    links = {
        "records": Counter(),
        "items_total": 0,
        "item_types": Counter(),
        "item_keys": Counter(),
        "key_value_shapes": Counter(),
        "nested_keys": Counter(),
        "url_candidate_fields": Counter(),
        "url_candidate_schemes": Counter(),
        "items_with_no_direct_url_candidate": 0,
    }

    for level, fields in _FIELDS.items():
        shapes = {field: Counter() for field in fields}
        trimmed = Counter()
        scanned = 0
        for row in frames[level].to_local_iterator():
            source = _profile_json_obj(row)
            scanned += 1
            for field in fields:
                raw = source.get(field, _MISSING)
                if field in _TIMESTAMP_FIELDS:
                    label, differs = _profile_datetime_shape(raw)
                    trimmed[field] += int(differs)
                else:
                    label = _profile_finite_number(raw)
                shapes[field][label] += 1
            if level != "Source":
                continue
            raw_links = source.get("SOURCE_LINKS", _MISSING)
            if raw_links is _MISSING:
                links["records"]["MISSING_KEY"] += 1
                continue
            if raw_links is None:
                links["records"]["JSON_NULL"] += 1
                continue
            if not isinstance(raw_links, list):
                links["records"]["NON_ARRAY"] += 1
                continue
            links["records"]["NONEMPTY_ARRAY" if raw_links else "EMPTY_ARRAY"] += 1
            for item in raw_links:
                links["items_total"] += 1
                links["item_types"][_profile_kind(item)] += 1
                if not isinstance(item, dict):
                    continue
                has_url_candidate = False
                for key, value in item.items():
                    name = str(key)
                    links["item_keys"][name] += 1
                    links["key_value_shapes"][name + ":" + _profile_kind(value)] += 1
                    if isinstance(value, dict):
                        for child_key, child_value in value.items():
                            links["nested_keys"][
                                name + "." + str(child_key) + ":" + _profile_kind(child_value)
                            ] += 1
                    elif isinstance(value, list):
                        for child in value:
                            if isinstance(child, dict):
                                for child_key, child_value in child.items():
                                    links["nested_keys"][
                                        name + "[]." + str(child_key) + ":" + _profile_kind(child_value)
                                    ] += 1
                    normalized = re.sub(r"[^a-z]", "", name.lower())
                    if normalized in _URL_KEY_TOKENS:
                        has_url_candidate = True
                        links["url_candidate_fields"][name] += 1
                        links["url_candidate_schemes"][
                            name + ":" + _profile_url_scheme(value)
                        ] += 1
                if not has_url_candidate:
                    links["items_with_no_direct_url_candidate"] += 1
        if not scanned:
            raise ValueError("NO_CACHED_RECORDS_FOR_LEVEL: " + level)
        for field in fields:
            shape_counts = dict(sorted(shapes[field].items()))
            if sum(shape_counts.values()) != scanned:
                raise AssertionError("Field counts do not reconcile")
            result["fields"].append({
                "level": level, "field": field, "rows_scanned": scanned,
                "shape_counts": shape_counts,
                "surrounding_whitespace_count": int(trimmed[field])
                if field in _TIMESTAMP_FIELDS else None,
            })
    result["source_links"] = {
        "record_shapes": dict(sorted(links["records"].items())),
        "items_total": links["items_total"],
        "item_types": dict(sorted(links["item_types"].items())),
        "item_keys": _profile_key_summary(links["item_keys"]),
        "key_value_shapes": _profile_key_summary(links["key_value_shapes"]),
        "nested_key_shapes": _profile_key_summary(links["nested_keys"]),
        "possible_url_field_counts": dict(sorted(links["url_candidate_fields"].items())),
        "possible_url_scheme_counts": dict(sorted(links["url_candidate_schemes"].items())),
        "items_with_no_direct_url_candidate": links["items_with_no_direct_url_candidate"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


OSCAL_NEXT_MAPPING_DETAIL_GATES = run_source_two_next_mapping_detail_gates()
