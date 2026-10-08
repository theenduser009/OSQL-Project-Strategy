# Source Two Topic read-only discovery: physical table, fields, and parent links.
# Run ONE NEW PYTHON cell in the existing mapper notebook after Cell 1 is loaded.
# No client-specific table names, source field inventory, IDs, or inputs required.
# This does not execute the mapper or modify a DIM, FACT or registry.

import json
import re

if "session" not in globals() or "SOURCE_FILES" not in globals():
    raise RuntimeError("Use the existing loaded mapper notebook with Cell 1.")

profiles = [
    p for p in SOURCE_FILES
    if "CATALOG" in p.get("MODEL_BINDINGS", ()) and p.get("RAW_TABLE")
]
if len(profiles) != 1:
    raise RuntimeError("Exactly one configured Source Two Catalog source is required.")
source = profiles[0]
parts = source["RAW_TABLE"].split(".")
if len(parts) != 3 or not all(
    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", s) for s in parts
):
    raise RuntimeError("Current RAW table identifier needs review.")
database, schema, source_table_name = parts
if not source_table_name.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Source Two RAW naming convention needs review.")
family = source_table_name[:-len("_SOURCE_RAW")].upper()

def quote_sql(value):
    return "'" + str(value).replace("'", "''") + "'"

# Query actual Snowflake metadata. An exact Topic table is not assumed.
table_sql = f"""
SELECT TABLE_NAME, ROW_COUNT
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA={quote_sql(schema.upper())}
  AND TABLE_NAME ILIKE '%TOPIC%'
ORDER BY TABLE_NAME
"""
options = [r.as_dict() for r in session.sql(table_sql).collect()]
print("SOURCE TWO TOPIC: PHYSICAL TABLE CANDIDATES")
print(json.dumps(options, indent=2, default=str))
matching = [r for r in options
            if str(r["TABLE_NAME"]).upper().startswith(family + "_")
            and str(r["TABLE_NAME"]).upper().endswith("_RAW")]
if len(matching) != 1:
    raise RuntimeError("Topic table ambiguous or not found; review candidates first.")
name = str(matching[0]["TABLE_NAME"])
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
    raise RuntimeError("Unexpected table name returned by source metadata.")
topic = f"{database}.{schema}.{name}"

columns = {c.upper() for c in session.table(topic).columns}
if not {"CONTENT_ID", "CURATED_JSON"}.issubset(columns):
    raise RuntimeError("Topic RAW lacks CONTENT_ID or CURATED_JSON.")

identity_sql = f"""
SELECT COUNT(*) AS TOPIC_RAW_ROWS,
       COUNT(DISTINCT CONTENT_ID::VARCHAR) AS DISTINCT_CONTENT_IDS,
       COALESCE(COUNT_IF(CONTENT_ID IS NULL OR TRIM(CONTENT_ID::VARCHAR)=''),0)
         AS MISSING_CONTENT_IDS,
       COALESCE(COUNT_IF(CURATED_JSON IS NULL),0) AS NULL_CURATED_JSON,
       COALESCE(COUNT_IF(TYPEOF(CURATED_JSON)<>'OBJECT'),0) AS NON_OBJECT_JSON
FROM {topic}
"""
identity = session.sql(identity_sql).collect()[0].as_dict()
print("TOPIC RAW IDENTITIES AND CURATED_JSON")
print(json.dumps(identity, indent=2, default=str))
if identity["NON_OBJECT_JSON"] != 0:
    raise RuntimeError("Non-object Topic CURATED_JSON needs inspection before profiling.")

inventory_sql = f"""
SELECT f.VALUE::VARCHAR AS FIELD_NAME,
       COUNT(*) AS ROWS_WITH_FIELD,
       COALESCE(COUNT_IF(
         GET(t.CURATED_JSON, f.VALUE::STRING) IS NOT NULL AND
         NOT IS_NULL_VALUE(GET(t.CURATED_JSON, f.VALUE::STRING))
       ),0) AS POPULATED_ROWS,
       MIN(TYPEOF(GET(t.CURATED_JSON, f.VALUE::STRING))) AS TYPE_SAMPLE
FROM {topic} t,
     LATERAL FLATTEN(INPUT=>OBJECT_KEYS(t.CURATED_JSON)) f
GROUP BY f.VALUE::VARCHAR
ORDER BY FIELD_NAME
"""
fields = [r.as_dict() for r in session.sql(inventory_sql).collect()]
related = [f for f in fields if any(
    word in f["FIELD_NAME"].upper()
    for word in ("TOPIC", "SOURCE", "SECTION", "CONTROL", "POLICY", "REFERENCE")
)]
print("TOPIC JSON FIELDS RELEVANT TO CATALOG HIERARCHY")
print(json.dumps(related[:75], indent=2, default=str))
print("Distinct Topic JSON fields:", len(fields))

references = [f for f in fields if (
    "SOURCE" in f["FIELD_NAME"].upper()
    and any(w in f["FIELD_NAME"].upper() for w in ("REF", "PARENT"))
)]
print("POTENTIAL TOPIC -> SOURCE REFERENCE FIELD")
print(json.dumps(references, indent=2, default=str))
if len(references) == 1:
    parent_field = references[0]["FIELD_NAME"]
    source_raw = source["RAW_TABLE"]
    relationship_sql = f"""
    WITH sources AS (
      SELECT DISTINCT CONTENT_ID::VARCHAR AS SOURCE_CONTENT_ID
      FROM {source_raw}
    ),
    refs AS (
      SELECT t.CONTENT_ID::VARCHAR AS TOPIC_CONTENT_ID,
             r.VALUE AS REF_VALUE,
             r.VALUE:"ContentId"::VARCHAR AS REF_PARENT_CONTENT_ID
      FROM {topic} t,
           LATERAL FLATTEN(
             INPUT=>GET(t.CURATED_JSON,{quote_sql(parent_field)}),
             OUTER=>TRUE
           ) r
    ),
    per_topic AS (
      SELECT TOPIC_CONTENT_ID,
             COALESCE(COUNT_IF(REF_VALUE IS NOT NULL),0) AS N
      FROM refs GROUP BY TOPIC_CONTENT_ID
    )
    SELECT
      (SELECT COUNT(*) FROM per_topic) AS DISTINCT_TOPICS_CHECKED,
      (SELECT COALESCE(COUNT_IF(N=0),0) FROM per_topic) AS TOPICS_WITH_NO_SOURCE_REF,
      (SELECT COALESCE(COUNT_IF(N=1),0) FROM per_topic) AS TOPICS_WITH_ONE_SOURCE_REF,
      (SELECT COALESCE(COUNT_IF(N>1),0) FROM per_topic) AS TOPICS_WITH_MULTIPLE_SOURCE_REFS,
      COALESCE(COUNT_IF(r.REF_VALUE IS NOT NULL),0) AS SOURCE_REF_ITEMS,
      COALESCE(COUNT_IF(r.REF_VALUE IS NOT NULL
                        AND r.REF_PARENT_CONTENT_ID IS NULL),0) AS MISSING_PARENT_IDS,
      COALESCE(COUNT_IF(r.REF_VALUE IS NOT NULL
                        AND s.SOURCE_CONTENT_ID IS NULL),0) AS UNMATCHED_PARENT_REFS,
      COUNT(DISTINCT s.SOURCE_CONTENT_ID) AS DISTINCT_MATCHED_SOURCES
    FROM refs r
    LEFT JOIN sources s ON s.SOURCE_CONTENT_ID = r.REF_PARENT_CONTENT_ID
    """
    result = session.sql(relationship_sql).collect()[0].as_dict()
    print("TOPIC -> AUTHORITATIVE SOURCE REFERENCE COVERAGE")
    print(json.dumps(result, indent=2, default=str))
    print("Reference child key ContentId is an inspection hypothesis; "
          "verify it from real item shape before accepting relationships.")
else:
    print("Cannot choose one parent-reference field; no parent join attempted.")

print("DONE: Source Two Topic discovery only. No mapper or target writes.")
