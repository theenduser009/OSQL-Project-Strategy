# %% Source Two — next Sub-Section prose-field profile
# COPY/RUN: one NEW Python cell in Snowflake DEV. Read-only, 2026-10-14.
# Profiles only the two newly proposed scalar text parts; prints counts, no source values.
# No fixed company/database/schema identifier is published in this public script.
import json
import re
from snowflake.snowpark.context import get_active_session

_session = get_active_session()
if _session is None:
    raise RuntimeError("Open this cell in a connected Snowflake notebook.")

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SOURCE_SUFFIX = "_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW"

def _ident(value):
    if not isinstance(value, str) or not _SAFE_IDENTIFIER.fullmatch(value):
        raise RuntimeError("Unexpected metadata identifier. No source data query ran.")
    return '"' + value + '"'

# Discover this one source RAW table without publishing a client namespace.
# If more than one is visible, STOP; do not guess DEV/PROD or choose a row arbitrarily.
_show = _session.sql(
    "SHOW TERSE TABLES LIKE '%AUTHORITATIVE_SOURCES_SUB_SECTION_RAW' IN ACCOUNT"
).collect()
_candidates = set()
for _row in _show:
    _metadata = _row.as_dict(recursive=True)
    _metadata = {str(k).lower(): v for k, v in _metadata.items()}
    _table = str(_metadata.get("name") or "")
    _db = str(_metadata.get("database_name") or "")
    _schema = str(_metadata.get("schema_name") or "")
    if _table.upper().endswith(_SOURCE_SUFFIX):
        _candidates.add((_db, _schema, _table))
if len(_candidates) != 1:
    print("MATCHING_RAW_TABLE_COUNT:", len(_candidates))
    raise RuntimeError("Expected exactly one accessible Authoritative Sources Sub-Section RAW table; review scope before continuing.")
_database, _schema, _table = next(iter(_candidates))
_source = ".".join(_ident(x) for x in (_database, _schema, _table))

# Fixed field names. Only aggregate counts come back; no Content IDs or payload values.
_query = """
WITH inspected AS (
    SELECT fields.FIELD_NAME,
           GET(raw.CURATED_JSON, fields.FIELD_NAME) AS RAW_VALUE
    FROM {source} raw
    CROSS JOIN (
        SELECT 'SUB_SECTION_DESCRIPTION' AS FIELD_NAME
        UNION ALL SELECT 'INFORMATION' AS FIELD_NAME
    ) fields
)
SELECT FIELD_NAME,
       COUNT(*) AS SOURCE_RECORDS,
       COALESCE(COUNT_IF(RAW_VALUE IS NULL OR IS_NULL_VALUE(RAW_VALUE)),0) AS ABSENT_OR_JSON_NULL,
       COALESCE(COUNT_IF(TYPEOF(RAW_VALUE)='VARCHAR'
           AND NULLIF(TRIM(RAW_VALUE::VARCHAR),'') IS NOT NULL),0) AS POPULATED_TEXT,
       COALESCE(COUNT_IF(TYPEOF(RAW_VALUE)='VARCHAR'
           AND NULLIF(TRIM(RAW_VALUE::VARCHAR),'') IS NULL),0) AS BLANK_TEXT,
       COALESCE(COUNT_IF(TYPEOF(RAW_VALUE) NOT IN ('VARCHAR','NULL_VALUE')
           AND RAW_VALUE IS NOT NULL),0) AS NON_TEXT_SHAPE,
       COALESCE(COUNT_IF(TYPEOF(RAW_VALUE)='VARCHAR'
           AND REGEXP_LIKE(RAW_VALUE::VARCHAR, '.*<[^>]+>.*','s')),0) AS HTML_LIKE_TEXT
FROM inspected
GROUP BY FIELD_NAME
ORDER BY FIELD_NAME
""".format(source=_source)
_rows = [_row.as_dict(recursive=True) for _row in _session.sql(_query).collect()]
if len(_rows) != 2 or {str(x.get("FIELD_NAME")) for x in _rows} != {
        "SUB_SECTION_DESCRIPTION", "INFORMATION"}:
    raise RuntimeError("Unexpected field inventory in source profile; review required.")

print("SOURCE_TWO_NEXT_SUBSECTION_PARTS_READ_ONLY_PROFILE")
for _item in sorted(_rows, key=lambda x: str(x["FIELD_NAME"])):
    _field = str(_item["FIELD_NAME"])
    _total = int(_item["SOURCE_RECORDS"])
    _populated = int(_item["POPULATED_TEXT"])
    _blank = int(_item["BLANK_TEXT"])
    _absent = int(_item["ABSENT_OR_JSON_NULL"])
    _nontext = int(_item["NON_TEXT_SHAPE"])
    _html = int(_item["HTML_LIKE_TEXT"])
    if _absent + _blank + _populated + _nontext != _total or _html > _populated:
        raise RuntimeError("Source field shape bucket counts do not reconcile for " + _field)
    _decision = (
        "REVIEW_SHAPE_OR_SOURCE_DRIFT" if _total != 20000 or _nontext != 0
        else "CANDIDATE_TEXT_SOURCE_POPULATED" if _populated > 0
        else "NO_POPULATED_SOURCE_DATA"
    )
    print(json.dumps({
        "FIELD": _field, "SOURCE_RECORDS": _total,
        "POPULATED_TEXT": _populated, "BLANK_TEXT": _blank,
        "ABSENT_OR_JSON_NULL": _absent, "NON_TEXT_SHAPE": _nontext,
        "HTML_LIKE_TEXT": _html, "PROFILE_DECISION": _decision
    }, sort_keys=True))
print("READ_ONLY_COMPLETE: no registry, source, DIM/FACT writes, mapper run, or COMMIT.")
