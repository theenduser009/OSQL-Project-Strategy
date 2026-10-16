# %% Source Two — native Control Standard ID/title candidates, nonempty values
# ONE standalone Python cell in a connected Snowflake notebook; SELECT-only.
# The previously verified direct CONTROL_STANDARDS integer references already
# resolve to target RAW CONTENT_ID. Do NOT repeat that acceptance query.
# This profiles *business id and title fields* on referenced target records.

import json
import re

try:
    _session = session
except NameError:
    _session = None
if _session is None:
    try:
        from snowflake.snowpark.context import get_active_session
        _session = get_active_session()
    except Exception:
        raise RuntimeError("Open this cell in a connected Snowflake notebook.") from None
if _session is None:
    raise RuntimeError("No active Snowflake session.")
session = _session

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

def identifier(value):
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise RuntimeError("Unsupported source identifier; no business SELECT ran.")
    return '"' + value + '"'

def literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def fetch(statement):
    return [row.as_dict(recursive=True) for row in session.sql(statement).collect()]

# One metadata-only lookup, no assumption that the notebook's current schema
# is the RAW schema. Only accept a single target visible to this role.
raw_tables = fetch("SHOW TERSE TABLES LIKE '%CONTROL_STANDARDS_RAW' IN ACCOUNT")
options = []
for row in raw_tables:
    name = str(row.get("name") or row.get("NAME") or "").upper()
    db = str(row.get("database_name") or row.get("DATABASE_NAME") or "")
    schema = str(row.get("schema_name") or row.get("SCHEMA_NAME") or "")
    if name.endswith("_CONTROL_STANDARDS_RAW") and all(
            _SAFE.fullmatch(s) for s in (db, schema, name)):
        options.append((db, schema, name))
options = sorted(set(options))
if len(options) != 1:
    print(json.dumps({"TARGET_CANDIDATES": [
        {"database": d, "schema": s, "table": t}
        for d, s, t in options[:15]], "COUNT": len(options)}, indent=2))
    raise RuntimeError("Expected exactly one accessible Control Standards RAW target.")
database, schema, target = options[0]

# Metadata-only discovery of the already-accepted four-level source family
# in the same namespace. Does NOT run the old 39,897-item match validation.
table_rows = fetch(
    "SELECT TABLE_NAME FROM " + identifier(database) + ".INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_SCHEMA = " + literal(schema.upper()) +
    " AND TABLE_NAME LIKE '%RAW' ORDER BY TABLE_NAME")
available = {str(row["TABLE_NAME"]).upper() for row in table_rows}
if any(not _SAFE.fullmatch(s) for s in available):
    raise RuntimeError("Unexpected RAW table identifier in metadata.")
source_families = []
for source_table in sorted(available):
    if not source_table.endswith("_SOURCE_RAW"):
        continue
    base = source_table[:-len("_SOURCE_RAW")]
    if all(base + suffix in available for suffix in
           ("_TOPIC_RAW", "_SECTION_RAW", "_SUB_SECTION_RAW")):
        source_families.append(base)
if len(source_families) != 1 or target not in available:
    print(json.dumps({"SOURCE_FAMILY_COUNT": len(source_families)}, indent=2))
    raise RuntimeError("Control Standard target and four-level source family are ambiguous.")
base = source_families[0]

def full_table(table_name):
    return ".".join(identifier(part) for part in (database, schema, table_name))

source_tables = [base + suffix for suffix in
                 ("_SOURCE_RAW", "_TOPIC_RAW", "_SECTION_RAW", "_SUB_SECTION_RAW")]
references = [
    "SELECT f.VALUE::VARCHAR AS CONTROL_CONTENT_ID FROM " + full_table(name) +
    " s, LATERAL FLATTEN(INPUT => GET(s.CURATED_JSON, 'CONTROL_STANDARDS')) f"
    for name in source_tables
]
# Only the already matched target-record subset is inspected. We do not
# print Content IDs or actual source values, just coverage and value shapes.
sql = """
WITH all_direct_ref_ids AS (
""" + "\nUNION ALL\n".join(references) + """
), referenced_ids AS (
    SELECT DISTINCT CONTROL_CONTENT_ID FROM all_direct_ref_ids
), referenced_controls AS (
    SELECT t.CONTENT_ID::VARCHAR AS CONTROL_CONTENT_ID, t.CURATED_JSON
    FROM """ + full_table(target) + """ t
    JOIN referenced_ids r ON r.CONTROL_CONTENT_ID = t.CONTENT_ID::VARCHAR
), candidate_values AS (
    SELECT t.CONTROL_CONTENT_ID, k.VALUE::VARCHAR AS FIELD_NAME,
           GET(t.CURATED_JSON, k.VALUE::VARCHAR) AS FIELD_VALUE
    FROM referenced_controls t,
         LATERAL FLATTEN(INPUT => OBJECT_KEYS(t.CURATED_JSON)) k
    WHERE REGEXP_LIKE(UPPER(k.VALUE::VARCHAR),
          '.*(STANDARD|TITLE|NAME|DESCRIPTION|REQUIREMENT|CONTROL_ID).*')
), normalized AS (
    SELECT CONTROL_CONTENT_ID, FIELD_NAME, FIELD_VALUE,
           TYPEOF(FIELD_VALUE) AS VALUE_TYPE,
           CASE WHEN TYPEOF(FIELD_VALUE) IN
               ('VARCHAR','INTEGER','DECIMAL','DOUBLE','BOOLEAN')
                THEN NULLIF(TRIM(TO_VARCHAR(FIELD_VALUE)), '')
                ELSE NULL END AS SCALAR_TEXT
    FROM candidate_values
)
SELECT FIELD_NAME, VALUE_TYPE,
       (SELECT COUNT(*) FROM referenced_controls) AS REFERENCED_CONTROL_RECORDS,
       COUNT(*) AS RECORDS_WITH_KEY,
       COUNT_IF(SCALAR_TEXT IS NOT NULL) AS NONEMPTY_SCALAR_RECORDS,
       COUNT(DISTINCT SCALAR_TEXT) AS DISTINCT_NONEMPTY_SCALAR_VALUES,
       COUNT_IF(FIELD_VALUE IS NULL OR IS_NULL_VALUE(FIELD_VALUE)) AS NULL_VALUES,
       COUNT_IF(VALUE_TYPE IN ('VARCHAR','INTEGER','DECIMAL','DOUBLE','BOOLEAN')
                AND SCALAR_TEXT IS NULL) AS BLANK_SCALAR_VALUES,
       COUNT_IF(VALUE_TYPE IN ('OBJECT','ARRAY')) AS STRUCTURED_VALUES,
       MIN(LENGTH(SCALAR_TEXT)) AS MIN_NONEMPTY_LENGTH,
       MAX(LENGTH(SCALAR_TEXT)) AS MAX_NONEMPTY_LENGTH
FROM normalized
GROUP BY FIELD_NAME, VALUE_TYPE
ORDER BY NONEMPTY_SCALAR_RECORDS DESC, DISTINCT_NONEMPTY_SCALAR_VALUES DESC,
         FIELD_NAME
LIMIT 80
"""
rows = fetch(sql)
print("SOURCE TWO: POPULATED CONTROL STANDARD ID/TITLE CANDIDATES")
print(json.dumps({
    "TARGET_RAW_TABLE": target,
    "CANDIDATE_COUNTS": rows,
    "STATUS": "BUSINESS_ID_AND_TITLE_SELECTION_PENDING_OWNER_PREVIEW",
}, indent=2, default=str))
print("Key presence alone is NOT a populated business value.")
print("A distinct Archer Content ID is NOT an approved native OSCAL control id.")
print("DONE: metadata and aggregate read-only checks only; no target writes.")
