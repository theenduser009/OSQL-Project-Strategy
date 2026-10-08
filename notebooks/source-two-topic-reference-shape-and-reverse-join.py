# Source Two Topic parent-link discovery: inspect both reference directions.
# Paste into ONE new Python cell in the already-loaded Snowflake mapper notebook.
# Read-only; no manual tables, mapping CSV, Content IDs, or COMMIT.
# Values printed by this cell stay in the owner's Snowflake notebook.

import json
import re

if "session" not in globals() or "SOURCE_FILES" not in globals():
    raise RuntimeError("Use the existing mapper notebook with Cell 1 loaded.")

profiles = [p for p in SOURCE_FILES
            if "CATALOG" in p.get("MODEL_BINDINGS", ()) and p.get("RAW_TABLE")]
if len(profiles) != 1:
    raise RuntimeError("Expected one configured Source Two Catalog source.")

src = profiles[0]["RAW_TABLE"]
parts = src.split(".")
if len(parts) != 3 or not all(
    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", x) for x in parts
):
    raise RuntimeError("Invalid existing configured source-table identifier.")
db, schema, basename = parts
if not basename.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Expected Source-level RAW table naming contract.")
topic_name = basename[:-len("_SOURCE_RAW")] + "_TOPIC_RAW"
topic = f"{db}.{schema}.{topic_name}"

def sq(v):
    return "'" + str(v).replace("'", "''") + "'"

def get_rows(sql):
    return [r.as_dict() for r in session.sql(sql).collect()]

exists = get_rows(f"""
    SELECT COUNT(*) AS N FROM {db}.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = {sq(schema.upper())}
      AND TABLE_NAME = {sq(topic_name.upper())}
""")[0]["N"]
if exists != 1:
    raise RuntimeError("The previously discovered Topic RAW table is not found.")

def keys_in(table):
    return [x["NAME"] for x in get_rows(f"""
        SELECT DISTINCT f.KEY::VARCHAR AS NAME
        FROM {table} t, LATERAL FLATTEN(INPUT=>t.CURATED_JSON) f
        WHERE f.KEY IS NOT NULL
    """)]

topic_keys = keys_in(topic)
source_keys = keys_in(src)
forward_names = [x for x in topic_keys
                 if "SOURCE" in x.upper() and "REF" in x.upper()]
reverse_names = [x for x in source_keys
                 if "TOPIC" in x.upper() and "REF" in x.upper()]

print("SOURCE TWO: TOPIC REFERENCE SHAPE / REVERSE JOIN")
print(json.dumps({
    "TOPIC_PARENT_REF_FIELDS": forward_names,
    "SOURCE_TOPIC_REF_FIELDS": reverse_names
}, indent=2))

def show_examples(table, field, heading):
    rows = get_rows(f"""
        SELECT TYPEOF(f.VALUE) AS ITEM_TYPE, TO_JSON(f.VALUE) AS REF_JSON
        FROM {table} t,
             LATERAL FLATTEN(INPUT=>GET(t.CURATED_JSON,{sq(field)})) f
        LIMIT 3
    """)
    print(heading)
    for row in rows:
        raw = row["REF_JSON"]
        try:
            parsed = json.loads(raw) if raw is not None else None
        except (TypeError, ValueError):
            parsed = raw
        print(json.dumps({
            "ITEM_TYPE": row["ITEM_TYPE"],
            "ITEM_KEYS": sorted(parsed.keys()) if isinstance(parsed, dict) else None,
            "ITEM_PREVIEW": json.dumps(parsed, ensure_ascii=False, default=str)[:500]
        }, ensure_ascii=False))

if len(forward_names) == 1:
    show_examples(topic, forward_names[0], "TOPIC -> SOURCE: 3 sample reference items")
else:
    print("TOPIC -> SOURCE: no unique source reference field; do not infer key.")

if len(reverse_names) == 1:
    name = reverse_names[0]
    show_examples(src, name, "SOURCE -> TOPIC: 3 sample reference items")

    reverse_sql = f"""
    WITH ref_items AS (
      SELECT s.CONTENT_ID::VARCHAR AS SOURCE_CONTENT_ID,
             r.VALUE:"ContentId"::VARCHAR AS REF_TOPIC_CONTENT_ID,
             r.VALUE:"LevelId"::VARCHAR AS REF_TOPIC_LEVEL_ID
      FROM {src} s,
           LATERAL FLATTEN(INPUT=>GET(s.CURATED_JSON,{sq(name)})) r
    ),
    linked AS (
      SELECT x.SOURCE_CONTENT_ID,
             x.REF_TOPIC_CONTENT_ID,
             x.REF_TOPIC_LEVEL_ID,
             t.CONTENT_ID::VARCHAR AS MATCHED_TOPIC_CONTENT_ID
      FROM ref_items x
      LEFT JOIN {topic} t
        ON t.CONTENT_ID::VARCHAR=x.REF_TOPIC_CONTENT_ID
    ),
    per_topic AS (
      SELECT MATCHED_TOPIC_CONTENT_ID,
             COUNT(DISTINCT SOURCE_CONTENT_ID) AS PARENTS
      FROM linked
      WHERE MATCHED_TOPIC_CONTENT_ID IS NOT NULL
      GROUP BY MATCHED_TOPIC_CONTENT_ID
    )
    SELECT
      (SELECT COUNT(*) FROM {topic}) AS TOPIC_RAW_ROWS,
      (SELECT COUNT(DISTINCT CONTENT_ID::VARCHAR) FROM {topic})
        AS DISTINCT_TOPIC_CONTENT_IDS,
      COUNT(*) AS SOURCE_REFERENCE_ITEMS,
      COALESCE(COUNT_IF(REF_TOPIC_CONTENT_ID IS NULL),0)
        AS ITEMS_WITHOUT_TOPIC_CONTENT_ID,
      COALESCE(COUNT_IF(REF_TOPIC_CONTENT_ID IS NOT NULL
                        AND MATCHED_TOPIC_CONTENT_ID IS NULL),0)
        AS UNMATCHED_TOPIC_REFERENCE_ITEMS,
      COUNT(DISTINCT MATCHED_TOPIC_CONTENT_ID) AS MATCHED_DISTINCT_TOPICS,
      COUNT(DISTINCT SOURCE_CONTENT_ID) AS SOURCES_WITH_REFERENCES,
      (SELECT COALESCE(COUNT_IF(PARENTS=1),0) FROM per_topic)
        AS TOPICS_WITH_ONE_SOURCE_PARENT,
      (SELECT COALESCE(COUNT_IF(PARENTS>1),0) FROM per_topic)
        AS TOPICS_WITH_MULTIPLE_SOURCE_PARENTS,
      (SELECT COUNT(DISTINCT CONTENT_ID::VARCHAR) FROM {topic})
        - COUNT(DISTINCT MATCHED_TOPIC_CONTENT_ID)
        AS TOPICS_NOT_LINKED_FROM_SOURCE
    FROM linked
    """
    output = get_rows(reverse_sql)[0]
    print("SOURCE -> TOPIC: MATCHING CONTENT IDS AND PARENT COVERAGE")
    print(json.dumps(output, indent=2, default=str))
    print("This confirms identity matches only if returned parent counts support it. "
          "The link is NOT an approved OSCAL parent edge yet.")
else:
    print("SOURCE -> TOPIC: no unique topic reference field; join not attempted.")

print("DONE: inspection only. No mapper, registry, Catalog DIM or FACT writes.")
