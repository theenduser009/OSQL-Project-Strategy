# %% OSCAL Source Two — next Topic/Section Catalog field discovery
# Dated 2026-10-15. ONE READ-ONLY Python cell in the EXISTING Snowflake DEV notebook.
# Uses the already retained four-level Source Two CURATED_JSON snapshot.
# Prints only aggregate counts/type distributions, never source values/record IDs.
# No SQL, registry changes, mapper rebuild, DIM/FACT writes or COMMIT.
import json
import re
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal

# Five candidate mappings plus one separately held diagnostic/roll-up.
_NEXT_FIELDS = {
    "topics": (
        ("DOCUMENT_NUMBER", "TEXT", "catalog.groups[].props[document-number]", "CANDIDATE"),
        ("TOTAL_NUMBER_OF_SECTIONS", "NUMBER", "catalog.groups[].props[section-count]", "CANDIDATE"),
    ),
    "sections": (
        ("SECTION_SHORT_DESCRIPTION", "TEXT", "catalog.groups[].groups[].props[short-description]", "CANDIDATE"),
        ("TOTAL_NUMBER_OF_SUB_SECTIONS", "NUMBER", "catalog.groups[].groups[].props[sub-section-count]", "CANDIDATE"),
        ("INFORMATION", "TEXT", "catalog.groups[].groups[].parts[information].prose", "CANDIDATE"),
        ("SUM_OF_SUB_SECTION_CRITICALITY_VALUE", "NUMBER", "UNRESOLVED_WORKSHEET_PATH", "DIAGNOSTIC_ONLY"),
    ),
}
_EXPECTED = {"topics": 1416, "sections": 10566}

_source_inputs = globals().get("SOURCE_INPUTS")
if not isinstance(_source_inputs, dict) or "source-two-source" not in _source_inputs:
    raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_REQUIRES_CACHED_SOURCE_TWO_INPUTS")
_cache = _source_inputs["source-two-source"].get("lookups", {}).get("joined_sources", {})
if not isinstance(_cache, dict):
    raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_REQUIRES_JOINED_SOURCE_CACHE")

_profile = globals().get("SOURCE_PROFILES")
if isinstance(_profile, list):
    _source_profiles = [p for p in _profile if p.get("SOURCE_KEY") == "source-two-source"]
    if len(_source_profiles) != 1 or _source_profiles[0].get("SOURCE_SYSTEM_NAME") != "ARCHER":
        raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_WRONG_SOURCE_PROFILE")

_select = globals().get("SELECTED_MODELS")
if _select is not None and tuple(_select) != ("CATALOG",):
    raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_REQUIRES_CATALOG_ONLY")

_scalar_types = {"TEXT", "NUMBER", "BOOLEAN", "OBJECT", "ARRAY", "TEMPORAL", "OTHER"}

def _kind(value):
    if isinstance(value, str):
        return "BLANK_TEXT" if not value.strip() else "TEXT"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, (int, float, Decimal)):
        return "NUMBER"
    if isinstance(value, dict):
        return "OBJECT"
    if isinstance(value, list):
        return "ARRAY"
    if isinstance(value, (date, datetime, time)):
        return "TEMPORAL"
    return "OTHER"


def _read_doc(record):
    payload = record["CURATED_JSON"]
    python_converter = globals().get("_to_python")
    if callable(python_converter):
        payload = python_converter(payload)
    if isinstance(payload, str):
        payload = json.loads(payload, parse_float=Decimal)
    if not isinstance(payload, dict):
        raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_INVALID_CURATED_JSON_OBJECT")
    return payload


def _field_result(counter, expected, record_count):
    populated = sum(counter[k] for k in _scalar_types)
    missing = counter["MISSING_KEY"] + counter["JSON_NULL"]
    if populated + missing + counter["BLANK_TEXT"] != record_count:
        raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_COUNT_RECONCILIATION_FAILED")
    if populated == 0:
        return "DEFER_NO_POPULATED_SOURCE"
    if counter["BLANK_TEXT"] or counter["OTHER"]:
        return "REVIEW_NONCANONICAL_SOURCE_VALUE"
    if expected == "TEXT" and populated == counter["TEXT"]:
        return "CANDIDATE_TEXT_SOURCE_READY_FOR_MAPPING_REVIEW"
    if expected == "NUMBER" and populated == counter["NUMBER"]:
        return "CANDIDATE_NUMERIC_SOURCE_READY_FOR_MAPPING_REVIEW"
    return "REVIEW_MIXED_OR_COMPLEX_SOURCE_TYPE"


print("SOURCE_TWO_NEXT_TOPIC_SECTION_CURATED_JSON_PROFILE_2026_10_15")
print("MODE: READ_ONLY_CACHED_SOURCE_SNAPSHOT")
for _level in ("topics", "sections"):
    _frame = _cache.get(_level)
    if _frame is None or not hasattr(_frame, "to_local_iterator"):
        raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_MISSING_" + _level.upper() + "_FRAME")
    _field_specs = _NEXT_FIELDS[_level]
    _counters = {name: Counter() for name, _, _, _ in _field_specs}
    _count, _identities = 0, set()
    for _row in _frame.to_local_iterator():
        _count += 1
        _cid = str(_row["_SOURCE_RECORD_ID"])
        if not _cid or _cid in _identities:
            raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_DUPLICATE_" + _level.upper() + "_RECORD")
        _identities.add(_cid)
        _doc = _read_doc(_row)
        for _name, _, _, _ in _field_specs:
            _c = _counters[_name]
            if _name not in _doc:
                _c["MISSING_KEY"] += 1
            elif _doc[_name] is None:
                _c["JSON_NULL"] += 1
            else:
                _value = _doc[_name]
                _category = _kind(_value)
                _c[_category] += 1
                if _category == "TEXT" and re.search(r"<[^>]+>", _value):
                    _c["HTML_LIKE_TEXT"] += 1
                if _category == "NUMBER" and _value == 0:
                    _c["NUMERIC_ZERO"] += 1
    print(_level.upper() + "_SOURCE_RECORDS:", _count)
    if _count != _EXPECTED[_level]:
        raise RuntimeError("NEXT_TOPIC_SECTION_PROFILE_SOURCE_SNAPSHOT_DRIFT_" + _level.upper())
    for _name, _type, _path, _role in _field_specs:
        _c = _counters[_name]
        _decision = _field_result(_c, _type, _count)
        if _role == "DIAGNOSTIC_ONLY" and _decision.startswith("CANDIDATE_"):
            _decision = "OWNER_REVIEW_ROLLUP_MEANING_AND_PATH"
        _output = {
            "level": _level.upper(), "field": _name,
            "source_records": _count,
            "source_populated": sum(_c[k] for k in _scalar_types),
            "missing_key": _c["MISSING_KEY"], "json_null": _c["JSON_NULL"],
            "blank_text": _c["BLANK_TEXT"], "text": _c["TEXT"],
            "number": _c["NUMBER"], "zero_number": _c["NUMERIC_ZERO"],
            "object": _c["OBJECT"], "array": _c["ARRAY"],
            "boolean": _c["BOOLEAN"], "temporal": _c["TEMPORAL"],
            "other": _c["OTHER"], "html_like_text": _c["HTML_LIKE_TEXT"],
            "proposed_path": _path, "profile_decision": _decision,
            "status": _role,
        }
        print(json.dumps(_output, sort_keys=True))
print("DONE: NO SOURCE/REGISTRY/DIM/FACT WRITES, NO PREVIEW OR COMMIT")
