# %% Source Two — one-batch Sub-Section scalar field source profiler
# Date: 2026-10-14. READ ONLY. Copy this ONE cell into Snowflake DEV.
# Eight fields, one source snapshot, aggregate counts only.
# No registry SQL, mapper reruns, target writes, COMMIT, or business values.
import json
import re

try:
    _scalar_profile_session = session
except NameError:
    _scalar_profile_session = None
if _scalar_profile_session is None:
    from snowflake.snowpark.context import get_active_session
    _scalar_profile_session = get_active_session()
if _scalar_profile_session is None:
    raise RuntimeError("Open in a connected Snowflake DEV notebook.")

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_FIELDS = (
    ("SUB_SECTION_SHORT_DESCRIPTION", "text"),
    ("SUBSECTION_CRITICALITY_VALUE", "direct"),
    ("SUB_SECTION_MAPPING_STATUS", "archer-select"),
    ("NUMBER_OF_CONTROL_STANDARDS_SUB_SECTION_LEVEL", "direct"),
    ("COUNT_OF_CONTROLS", "direct"),
    ("CONTENT_SOURCE", "archer-select"),
    ("SUB_SECTION_DATE_CREATED", "timestamp"),
    ("SUB_SECTION_LAST_UPDATED", "timestamp"),
)

def _safe_name(part):
    if not isinstance(part, str) or not _SAFE_IDENT.fullmatch(part):
        raise RuntimeError("Ambiguous or invalid source schema identifier")
    return '"' + part + '"'

# Require a single visible DEV Sub-Section table, not a guessed database.
_table_meta = _scalar_profile_session.sql(
    "SHOW TERSE TABLES LIKE '%AUTHORITATIVE_SOURCES_SUB_SECTION_RAW' IN ACCOUNT"
).collect()
_candidates = set()
for _item in _table_meta:
    _fields = {str(k).lower(): v for k, v in _item.as_dict(recursive=True).items()}
    _db = str(_fields.get("database_name") or "")
    _schema = str(_fields.get("schema_name") or "")
    _table = str(_fields.get("name") or "")
    if (_db.upper().endswith("_DEV")
            and _table.upper().endswith("_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW")
            and all(_SAFE_IDENT.fullmatch(x) for x in (_db, _schema, _table))):
        _candidates.add((_db, _schema, _table))
if len(_candidates) != 1:
    print("VISIBLE_DEV_SUBSECTION_RAW_CANDIDATES:", len(_candidates))
    raise RuntimeError("Exactly one visible DEV Authoritative Sources Sub-Section RAW table is required")

_db, _schema, _table = next(iter(_candidates))
_table_sql = ".".join(_safe_name(x) for x in (_db, _schema, _table))
_values = ",\n".join("('" + field + "', '" + transform + "')" for field, transform in _FIELDS)

# Aggregate field shape; no source record ID, payload text or values returned.
_sql = """
WITH source_fields AS (
    SELECT COLUMN1::VARCHAR AS FIELD_NAME, COLUMN2::VARCHAR AS EXPECTED_TRANSFORM
    FROM VALUES
    {values}
), parsed AS (
    SELECT f.FIELD_NAME, f.EXPECTED_TRANSFORM,
           GET(r.CURATED_JSON, f.FIELD_NAME) AS V
    FROM {source} r CROSS JOIN source_fields f
), shaped AS (
    SELECT FIELD_NAME, EXPECTED_TRANSFORM, V,
           COALESCE(TYPEOF(V), 'MISSING') AS VALUE_TYPE,
           IFF(V IS NULL OR IS_NULL_VALUE(V), 1, 0) AS NULL_OR_ABSENT,
           IFF(TYPEOF(V)='VARCHAR' AND NULLIF(TRIM(V::VARCHAR),'') IS NOT NULL, 1, 0)
               AS NONBLANK_TEXT,
           IFF(TYPEOF(V)='VARCHAR' AND NULLIF(TRIM(V::VARCHAR),'') IS NULL, 1, 0)
               AS BLANK_TEXT,
           IFF(TYPEOF(V) IN ('INTEGER','DECIMAL','DOUBLE'), 1, 0)
               AS NUMERIC_VALUE,
           IFF(TYPEOF(V)='BOOLEAN', 1, 0) AS BOOLEAN_VALUE,
           IFF(TYPEOF(V)='OBJECT', 1, 0) AS OBJECT_VALUE,
           IFF(TYPEOF(V)='ARRAY', 1, 0) AS ARRAY_VALUE,
           IFF(TYPEOF(V) IN ('TIMESTAMP_NTZ','TIMESTAMP_LTZ','TIMESTAMP_TZ','DATE','TIME'),1,0) AS TEMPORAL_VALUE,
           IFF(V IS NOT NULL AND NOT IS_NULL_VALUE(V) AND
               COALESCE(TYPEOF(V),'MISSING') NOT IN
               ('VARCHAR','INTEGER','DECIMAL','DOUBLE','BOOLEAN','OBJECT','ARRAY',
                'TIMESTAMP_NTZ','TIMESTAMP_LTZ','TIMESTAMP_TZ','DATE','TIME'),1,0) AS OTHER_VALUE,
           IFF(TYPEOF(V)='OBJECT' AND COALESCE(IS_ARRAY(GET(V,'ResolvedValues')),FALSE),
               1, 0) AS ARCHER_SELECT_WRAPPER,
           IFF(TYPEOF(V)='OBJECT' AND COALESCE(
               ARRAY_SIZE(GET(V,'ResolvedValues'))=1,FALSE),
               1, 0) AS SINGLE_RESOLVED_LABEL,
           IFF(TYPEOF(V)='VARCHAR'
               AND REGEXP_LIKE(V::VARCHAR,'.*<[^>]+>.*','s'),1,0) AS HTML_LIKE_TEXT
    FROM parsed
)
SELECT FIELD_NAME, EXPECTED_TRANSFORM,
       COUNT(*) AS SOURCE_RECORDS,
       SUM(NULL_OR_ABSENT) AS NULL_OR_ABSENT,
       SUM(NONBLANK_TEXT) AS NONBLANK_TEXT,
       SUM(BLANK_TEXT) AS BLANK_TEXT,
       SUM(NUMERIC_VALUE) AS NUMERIC_VALUE,
       SUM(BOOLEAN_VALUE) AS BOOLEAN_VALUE,
       SUM(OBJECT_VALUE) AS OBJECT_VALUE,
       SUM(ARRAY_VALUE) AS ARRAY_VALUE,
       SUM(TEMPORAL_VALUE) AS TEMPORAL_VALUE,
       SUM(OTHER_VALUE) AS OTHER_VALUE,
       SUM(ARCHER_SELECT_WRAPPER) AS ARCHER_SELECT_WRAPPER,
       SUM(SINGLE_RESOLVED_LABEL) AS SINGLE_RESOLVED_LABEL,
       SUM(HTML_LIKE_TEXT) AS HTML_LIKE_TEXT,
       LISTAGG(DISTINCT VALUE_TYPE, ', ') WITHIN GROUP (ORDER BY VALUE_TYPE)
           AS SOURCE_TYPES
FROM shaped GROUP BY FIELD_NAME, EXPECTED_TRANSFORM
ORDER BY FIELD_NAME
""".format(values=_values, source=_table_sql)
_rows = [r.as_dict(recursive=True) for r in _scalar_profile_session.sql(_sql).collect()]
if len(_rows) != len(_FIELDS) or {
        str(x.get("FIELD_NAME")) for x in _rows} != {
        name for name, _ in _FIELDS}:
    raise RuntimeError("Eight-field source inventory incomplete or duplicated")

print("SOURCE_TWO_SUBSECTION_NEXT_8_SCALARS_READ_ONLY_PROFILE")
for _row in sorted(_rows, key=lambda x: x["FIELD_NAME"]):
    _field = str(_row["FIELD_NAME"])
    _expected = dict(_FIELDS)[_field]
    _record_count = int(_row["SOURCE_RECORDS"])
    _null = int(_row["NULL_OR_ABSENT"])
    _text = int(_row["NONBLANK_TEXT"])
    _blank = int(_row["BLANK_TEXT"])
    _number = int(_row["NUMERIC_VALUE"])
    _bool = int(_row["BOOLEAN_VALUE"])
    _object = int(_row["OBJECT_VALUE"])
    _array = int(_row["ARRAY_VALUE"])
    _temporal = int(_row["TEMPORAL_VALUE"])
    _other = int(_row["OTHER_VALUE"])
    _select = int(_row["ARCHER_SELECT_WRAPPER"])
    _single = int(_row["SINGLE_RESOLVED_LABEL"])
    _html = int(_row["HTML_LIKE_TEXT"])
    _bucket_total = (_null + _text + _blank + _number + _bool + _object +
                     _array + _temporal + _other)
    if (_bucket_total != _record_count or _single > _select
            or _select > _object or _html > _text):
        raise RuntimeError("Unexpected source value type/bucket for " + _field)
    _populated = _record_count - _null - _blank
    if _record_count != 20000:
        _decision = "REVIEW_SOURCE_SNAPSHOT_DRIFT"
    elif _populated == 0:
        _decision = "DEFER_NO_POPULATED_SOURCE"
    elif _blank > 0:
        _decision = "REVIEW_BLANK_PRESENT_VALUES"
    elif _expected in ("text", "timestamp") and _populated != _text:
        _decision = "REVIEW_NON_TEXT_SHAPE"
    elif _expected == "archer-select" and _populated != _select:
        _decision = "REVIEW_NON_SELECT_SHAPE"
    elif _expected == "archer-select" and _single != _populated:
        _decision = "REVIEW_SELECT_CARDINALITY"
    elif _expected == "direct" and _populated != _number:
        _decision = "REVIEW_NON_NUMERIC_COUNT_SHAPE"
    else:
        _decision = "CANDIDATE_SHAPE_MATCH_REVIEW"
    print(json.dumps({
        "FIELD": _field, "EXPECTED_TRANSFORM": _expected,
        "SOURCE_RECORDS": _record_count,
        "POPULATED": _populated, "NULL_OR_ABSENT": _null,
        "NONBLANK_TEXT": _text, "BLANK_TEXT": _blank,
        "NUMERIC_VALUE": _number, "BOOLEAN_VALUE": _bool,
        "OBJECT_VALUE": _object, "ARRAY_VALUE": _array,
        "TEMPORAL_VALUE": _temporal, "OTHER_VALUE": _other,
        "ARCHER_SELECT_WRAPPER": _select, "SINGLE_RESOLVED_LABEL": _single,
        "HTML_LIKE_TEXT": _html,
        "SOURCE_TYPES": str(_row["SOURCE_TYPES"]),
        "SOURCE_GATE": _decision,
    }, sort_keys=True))
print("BATCH_STAGE: SOURCE_SHAPES_REVIEW_ONLY; NO TARGET PREVIEW/COMMIT")
print("DONE: SELECT-only source inventory, no source/registry/DIM/FACT writes.")
