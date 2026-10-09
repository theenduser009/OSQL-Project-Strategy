# %% Source Two direct Control Standards: resolve candidate target RAW IDs
# ONE standalone read-only Python cell in a connected Snowflake notebook.
# Source shape is already owner-verified: direct refs are INTEGER array items;
# descendant rollups are OBJECT items and are NEVER used as direct controls.
# Output is aggregate identity/key coverage; no data, registry or mapper writes.

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
        raise RuntimeError("Open this script in a connected Snowflake notebook.") from None
if _session is None:
    raise RuntimeError("No active Snowflake session is available.")
session = _session

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

def identifier(value):
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise RuntimeError("Unexpected Snowflake identifier; no reference query executed.")
    return '"' + value + '"'

def literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def fetch(sql):
    return [row.as_dict(recursive=True) for row in session.sql(sql).collect()]

# Resolve ONLY the current database/schema, not every account namespace.
current = fetch(
    "SELECT CURRENT_DATABASE() AS ACTIVE_DB, "
    "CURRENT_SCHEMA() AS ACTIVE_SCHEMA"
)
if len(current) != 1:
    raise RuntimeError("Could not identify the active database and schema.")
database = current[0].get("ACTIVE_DB")
schema = current[0].get("ACTIVE_SCHEMA")
if not isinstance(database, str) or not isinstance(schema, str):
    raise RuntimeError("Select a Source Two RAW database and schema.")
db_sql, schema_sql = identifier(database), identifier(schema)

table_list = fetch(
    "SELECT TABLE_NAME FROM " + db_sql + ".INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_SCHEMA = " + literal(schema.upper()) +
    " AND TABLE_NAME LIKE '%RAW' ORDER BY TABLE_NAME"
)
tables = {str(row["TABLE_NAME"]).upper() for row in table_list}
if not tables or not all(_SAFE.fullmatch(name) for name in tables):
    raise RuntimeError("No safe RAW table inventory in current schema.")

# The actual Source→Topic→Section→Sub-Section shape is established.
# A Control Standards app is DIFFERENT from the Authoritative Source tree.
families = []
for name in sorted(tables):
    if name.endswith("_SOURCE_RAW"):
        stem = name[:-len("_SOURCE_RAW")]
        if all(stem + suffix in tables for suffix in (
            "_TOPIC_RAW", "_SECTION_RAW", "_SUB_SECTION_RAW"
        )):
            families.append(stem)
if len(families) != 1:
    print(json.dumps({"AUTHORITATIVE_SOURCE_FAMILY_CANDIDATES": families}))
    raise RuntimeError(
        "Exactly one four-level Authoritative Sources RAW family is required "
        "in the selected database/schema."
    )
stem = families[0]
sources = (
    ("SOURCE", stem + "_SOURCE_RAW"),
    ("TOPIC", stem + "_TOPIC_RAW"),
    ("SECTION", stem + "_SECTION_RAW"),
    ("SUB_SECTION", stem + "_SUB_SECTION_RAW"),
)

# Target discovery is conservative: no guessed joins to Allocated Controls,
# Policies or the already mapped authoritative source hierarchy.
targets = sorted(name for name in tables
                 if "CONTROL_STANDARD" in name
                 and name not in {table for _, table in sources})
print(json.dumps({"CONTROL_STANDARD_RAW_CANDIDATES": targets}, indent=2))
if len(targets) != 1:
    raise RuntimeError(
        "Control Standards target RAW is missing or ambiguous. "
        "Review the reported candidates; no control reference join was run."
    )
target = targets[0]

columns = fetch(
    "SELECT COLUMN_NAME, DATA_TYPE FROM " + db_sql +
    ".INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = " +
    literal(schema.upper()) + " AND TABLE_NAME = " +
    literal(target) + " ORDER BY ORDINAL_POSITION"
)
present = {str(row["COLUMN_NAME"]).upper() for row in columns}
if not {"CONTENT_ID", "CURATED_JSON"} <= present:
    print(json.dumps({"TARGET_RAW_COLUMNS": sorted(present)}, indent=2))
    raise RuntimeError(
        "The candidate target must have CONTENT_ID and CURATED_JSON. "
        "No substitute identity column will be inferred."
    )

def table(name):
    return db_sql + "." + schema_sql + "." + identifier(name)

# Only directly owned CONTROL_STANDARDS integers; no rollup arrays are read.
parts = []
for level, name in sources:
    parts.append(
        "SELECT '" + level + "' AS OWNER_LEVEL, "
        "s.CONTENT_ID::VARCHAR AS OWNER_CONTENT_ID, "
        "f.VALUE AS REF_VALUE "
        "FROM " + table(name) + " s, "
        "LATERAL FLATTEN(INPUT => GET(s.CURATED_JSON, "
        "'CONTROL_STANDARDS')) f"
    )
cte = "WITH direct_items AS (\n" + "\nUNION ALL\n".join(parts) + "\n),\n"
cte += """
normalized AS (
    SELECT OWNER_LEVEL, OWNER_CONTENT_ID, REF_VALUE,
           CASE WHEN TYPEOF(REF_VALUE) = 'INTEGER'
                THEN REF_VALUE::VARCHAR ELSE NULL END AS CONTROL_CONTENT_ID
    FROM direct_items
),
target_rows AS (
    SELECT CONTENT_ID::VARCHAR AS CONTROL_CONTENT_ID, CURATED_JSON
    FROM """ + table(target) + """
),
target_ids AS (
    SELECT DISTINCT CONTROL_CONTENT_ID
    FROM target_rows
    WHERE CONTROL_CONTENT_ID IS NOT NULL
),
reference_ids AS (
    SELECT DISTINCT CONTROL_CONTENT_ID
    FROM normalized WHERE CONTROL_CONTENT_ID IS NOT NULL
)
"""

aggregate_sql = cte + """
SELECT n.OWNER_LEVEL,
       COUNT(*) AS DIRECT_REFERENCE_ITEMS,
       COUNT(DISTINCT n.OWNER_CONTENT_ID) AS OWNERS_WITH_REFERENCES,
       COUNT(DISTINCT n.CONTROL_CONTENT_ID) AS DISTINCT_CONTROL_REFERENCES,
       COALESCE(COUNT_IF(n.CONTROL_CONTENT_ID IS NULL), 0) AS NONINTEGER_ITEMS,
       COALESCE(COUNT_IF(t.CONTROL_CONTENT_ID IS NOT NULL), 0) AS MATCHED_ITEMS,
       COALESCE(COUNT_IF(t.CONTROL_CONTENT_ID IS NULL
                         AND n.CONTROL_CONTENT_ID IS NOT NULL), 0)
          AS UNMATCHED_ITEMS,
       COUNT(DISTINCT CASE WHEN t.CONTROL_CONTENT_ID IS NULL
                           THEN n.CONTROL_CONTENT_ID END)
          AS DISTINCT_UNMATCHED_IDS,
       (SELECT COUNT(*) FROM target_rows) AS TARGET_RECORDS,
       (SELECT COUNT(*) FROM target_ids) AS TARGET_DISTINCT_CONTENT_IDS,
       (SELECT COUNT(*) FROM target_rows
        WHERE CONTROL_CONTENT_ID IS NULL) AS TARGET_NULL_CONTENT_IDS
FROM normalized n
LEFT JOIN target_ids t ON t.CONTROL_CONTENT_ID = n.CONTROL_CONTENT_ID
GROUP BY n.OWNER_LEVEL
ORDER BY n.OWNER_LEVEL
"""
summary = fetch(aggregate_sql)
expected_levels = {level for level, _ in sources}
if {r["OWNER_LEVEL"] for r in summary} != expected_levels:
    raise RuntimeError("Direct Control Standards reference level output is incomplete.")
if any(r["TARGET_RECORDS"] != r["TARGET_DISTINCT_CONTENT_IDS"]
       or r["TARGET_NULL_CONTENT_IDS"] != 0 for r in summary):
    raise RuntimeError("Target candidate RAW Content IDs are not unique and populated.")

# Find likely native control ID/title source fields by field-NAME/type/coverage,
# not by exposing business values or assuming which fields to use.
keys_sql = cte + """
, matched_controls AS (
    SELECT t.CONTROL_CONTENT_ID, t.CURATED_JSON
    FROM target_rows t
    JOIN reference_ids r ON r.CONTROL_CONTENT_ID = t.CONTROL_CONTENT_ID
),
keys AS (
    SELECT m.CONTROL_CONTENT_ID, m.CURATED_JSON,
           k.VALUE::VARCHAR AS FIELD_NAME
    FROM matched_controls m,
         LATERAL FLATTEN(INPUT => OBJECT_KEYS(m.CURATED_JSON)) k
)
SELECT FIELD_NAME,
       TYPEOF(GET(CURATED_JSON, FIELD_NAME)) AS FIELD_VALUE_TYPE,
       COUNT(DISTINCT CONTROL_CONTENT_ID) AS MATCHED_CONTROLS_WITH_FIELD
FROM keys
WHERE FIELD_NAME ILIKE '%CONTROL%'
   OR FIELD_NAME ILIKE '%TITLE%'
   OR FIELD_NAME ILIKE '%NAME%'
   OR FIELD_NAME ILIKE '%IDENTIFIER%'
   OR UPPER(FIELD_NAME) = 'ID'
GROUP BY FIELD_NAME, FIELD_VALUE_TYPE
ORDER BY MATCHED_CONTROLS_WITH_FIELD DESC, FIELD_NAME
LIMIT 40
"""
keys = fetch(keys_sql)
print("SOURCE TWO CONTROL STANDARDS: DIRECT INTEGER-ID RECONCILIATION")
print(json.dumps({
    "TARGET_CONTROL_STANDARD_RAW": target,
    "DIRECT_ID_MATCH_SUMMARY": summary,
    "CONTROL_ID_TITLE_FIELD_CANDIDATES": keys,
    "MAPPING_STATUS": "TARGET_ID_AND_TITLE_SEMANTICS_STILL_REQUIRE_APPROVAL",
}, indent=2, default=str))
print("A matching Archer Content ID is not itself a native OSCAL control id.")
print("No rollup controls or missing target controls were created or inferred.")
print("DONE: metadata and aggregate SELECTs only; no source/registry/DIM/FACT writes.")
