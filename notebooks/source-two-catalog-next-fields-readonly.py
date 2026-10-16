# %% Read-only Source Two Catalog next-field profiler (2026-10-16)
# Use as ONE new cell in the already-running Snowflake DEV notebook.
# Reuses Cell 2 retained source/joined frames. Snowpark performs read-only SELECTs.
# No DDL, DML, MERGE, target-table modifications, or COMMIT.
# Prints field population and broad JSON shapes only: NO source values or Content IDs.

import datetime
import json
import re
from collections import Counter
from decimal import Decimal

OSCAL_CATALOG_NEXT_FIELDS = {
    "Source": ("SOURCE_LINKS", "DATE_CREATED", "LAST_UPDATED"),
    "Topic": ("TOPIC_DATE_CREATED", "TOPIC_LAST_UPDATED"),
    "Section": ("SUM_OF_SUB_SECTION_CRITICALITY_VALUE", "INFORMATION"),
    "Sub-Section": (
        "SUBSECTION_CRITICALITY_VALUE", "SUB_SECTION_DATE_CREATED",
        "SUB_SECTION_LAST_UPDATED", "INFORMATION",
    ),
}


def _source_two_profile_shape(value):
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, datetime.datetime):
        return "PY_DATETIME_AWARE" if value.tzinfo is not None else "PY_DATETIME_NAIVE"
    if isinstance(value, datetime.date):
        return "PY_DATE"
    if isinstance(value, (int, float, Decimal)):
        return "NUMBER"
    if isinstance(value, str):
        if not value.strip():
            return "EMPTY_TEXT"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return "ISO_DATE_TEXT"
        if re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}", value):
            return "TIMESTAMP_TEXT_WITH_OFFSET" if re.search(r"(?:[Zz]|[+-]\d{2}:\d{2})$", value) else "TIMESTAMP_TEXT_NO_OFFSET"
        return "TEXT"
    if isinstance(value, list):
        if not value:
            return "EMPTY_ARRAY"
        if all(isinstance(x, dict) for x in value):
            return "ARRAY_OBJECT"
        if all(not isinstance(x, (dict, list)) for x in value):
            return "ARRAY_SCALAR"
        return "ARRAY_MIXED_OR_NESTED"
    if isinstance(value, dict):
        return "EMPTY_OBJECT" if not value else "OBJECT"
    return "OTHER_TYPE"


def _source_two_profile_payload(record):
    raw = record["CURATED_JSON"]
    if hasattr(raw, "as_dict"):
        raw = raw.as_dict(recursive=True)
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("Cached CURATED_JSON must be an object")
    return raw


def run_source_two_catalog_next_fields_profile(namespace=None):
    scope = globals() if namespace is None else namespace
    source = scope.get("SOURCE_INPUTS", {}).get("source-two-source")
    if not source:
        raise ValueError("Cached source-two-source input missing; this profiler does not reload it")
    joins = source.get("lookups", {}).get("joined_sources", {})
    frames = {
        "Source": source.get("source_df"),
        "Topic": joins.get("topics"),
        "Section": joins.get("sections"),
        "Sub-Section": joins.get("subsections"),
    }
    if any(frame is None or not hasattr(frame, "to_local_iterator") for frame in frames.values()):
        raise ValueError("Cached Source Two four-level frames missing; no reload attempted")
    report = {"status": "READ_ONLY_SOURCE_TWO_CATALOG_FIELD_SHAPES",
              "writes_executed": False, "rows": []}
    missing = object()
    for level, fields in OSCAL_CATALOG_NEXT_FIELDS.items():
        counters = {field: Counter() for field in fields}
        count = 0
        for record in frames[level].to_local_iterator():
            payload = _source_two_profile_payload(record)
            count += 1
            for field in fields:
                value = payload.get(field, missing)  # EXACT Archer key; no aliases.
                label = ("MISSING_KEY" if value is missing else
                         "JSON_NULL" if value is None else _source_two_profile_shape(value))
                counters[field][label] += 1
        if count == 0:
            raise ValueError("No cached rows available for " + level)
        for field in fields:
            field_counts = dict(sorted(counters[field].items()))
            if sum(field_counts.values()) != count:
                raise AssertionError("Profiler count mismatch")
            report["rows"].append({"level": level, "field": field,
                                   "rows_scanned": count, "shape_counts": field_counts})
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


OSCAL_NEXT_FIELD_PROFILE = run_source_two_catalog_next_fields_profile()
