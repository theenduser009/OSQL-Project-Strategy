# Source Two Topic: independent reciprocal source-reference QA.
# READ ONLY. One new Python cell in the already-loaded mapper notebook.
# Source/table/field names come from the current Cell 1 and CURATED_JSON keys.

import json
import re

if "session" not in globals() or "SOURCE_FILES" not in globals():
    raise RuntimeError("Open the existing mapper notebook with Cell 1 loaded.")

profiles = [p for p in SOURCE_FILES
            if "CATALOG" in p.get("MODEL_BINDINGS", ()) and p.get("RAW_TABLE")]
if len(profiles) != 1:
    raise RuntimeError("Exactly one configured Source Two Catalog profile required.")
source_table = profiles[0]["RAW_TABLE"]
parts = source_table.split(".")
if len(parts) != 3 or not all(
    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", x) for x in parts
):
    raise RuntimeError("Unexpected configured source identifier.")
db, schema, basename = parts
if not basename.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Source naming pattern requires review.")
topic_table = f"{db}.{schema}.{basename[:-len('_SOURCE_RAW')]}_TOPIC_RAW"

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def read(sql):
    return [row.as_dict() for row in session.sql(sql).collect()]

def keys(table):
    return [r["KEY_NAME"] for r in read(f"""
      SELECT DISTINCT f.KEY::VARCHAR AS KEY_NAME
      FROM {table} t, LATERAL FLATTEN(INPUT=>t.CURATED_JSON) f
      WHERE f.KEY IS NOT NULL
    """)]

topic_keys = [x for x in keys(topic_table)
              if "SOURCE" in x.upper() and "REF" in x.upper()]
source_keys = [x for x in keys(source_table)
               if "TOPIC" in x.upper() and "REF" in x.upper()]

print("SOURCE TWO TOPIC — RECIPROCAL REFERENCE VALIDATION")
print(json.dumps({"TOPIC_TO_SOURCE_FIELD": topic_keys,
                  "SOURCE_TO_TOPIC_FIELD": source_keys}, indent=2))
if len(topic_keys) != 1 or len(source_keys) != 1:
    raise RuntimeError("Ambiguous parent/child reference fields; no join performed.")

sql = f"""
WITH source_ids AS (
  SELECT DISTINCT CONTENT_ID::VARCHAR AS SID FROM {source_table}
),
topic_ids AS (
  SELECT DISTINCT CONTENT_ID::VARCHAR AS TID FROM {topic_table}
),
forward_raw AS (
  SELECT t.CONTENT_ID::VARCHAR AS TID, r.VALUE::VARCHAR AS SID,
         TYPEOF(r.VALUE) AS ITEM_TYPE
  FROM {topic_table} t,
       LATERAL FLATTEN(INPUT=>GET(t.CURATED_JSON,{quote(topic_keys[0])})) r
),
reverse_raw AS (
  SELECT s.CONTENT_ID::VARCHAR AS SID,
         r.VALUE:"ContentId"::VARCHAR AS TID,
         r.VALUE:"LevelId"::VARCHAR AS LEVEL_ID
  FROM {source_table} s,
       LATERAL FLATTEN(INPUT=>GET(s.CURATED_JSON,{quote(source_keys[0])})) r
),
f AS (SELECT DISTINCT TID,SID FROM forward_raw),
r AS (SELECT DISTINCT TID,SID FROM reverse_raw),
parents AS (
  SELECT TID,COUNT(DISTINCT SID) AS N FROM f GROUP BY TID
)
SELECT
 (SELECT COUNT(*) FROM topic_ids) AS DISTINCT_TOPICS,
 (SELECT COUNT(*) FROM source_ids) AS DISTINCT_SOURCES,
 (SELECT COUNT(*) FROM forward_raw) AS TOPIC_TO_SOURCE_ITEMS,
 (SELECT COUNT(*) FROM forward_raw WHERE ITEM_TYPE='INTEGER')
    AS INTEGER_SOURCE_REFERENCE_ITEMS,
 (SELECT COUNT(*) FROM f
  JOIN source_ids s ON s.SID=f.SID) AS TOPIC_PARENT_IDS_FOUND,
 (SELECT COUNT(*) FROM f
  LEFT JOIN source_ids s ON s.SID=f.SID
  WHERE s.SID IS NULL) AS TOPIC_PARENT_IDS_NOT_FOUND,
 (SELECT COUNT(*) FROM parents WHERE N=1) AS TOPICS_WITH_ONE_PARENT_ID,
 (SELECT COUNT(*) FROM parents WHERE N>1) AS TOPICS_WITH_MULTIPLE_PARENT_IDS,
 (SELECT COUNT(*) FROM topic_ids t
  LEFT JOIN parents p ON p.TID=t.TID
  WHERE p.TID IS NULL OR p.N=0) AS TOPICS_WITHOUT_PARENT_ID,
 (SELECT COUNT(*) FROM reverse_raw) AS SOURCE_TO_TOPIC_ITEMS,
 (SELECT COUNT(*) FROM f) AS TOPIC_SIDE_DISTINCT_PAIRS,
 (SELECT COUNT(*) FROM r) AS SOURCE_SIDE_DISTINCT_PAIRS,
 (SELECT COUNT(*) FROM f JOIN r ON f.TID=r.TID AND f.SID=r.SID)
    AS RECIPROCAL_PAIRS,
 (SELECT COUNT(*) FROM f
  WHERE NOT EXISTS(SELECT 1 FROM r WHERE r.TID=f.TID AND r.SID=f.SID))
    AS TOPIC_SIDE_ONLY_PAIRS,
 (SELECT COUNT(*) FROM r
  WHERE NOT EXISTS(SELECT 1 FROM f WHERE f.TID=r.TID AND f.SID=r.SID))
    AS SOURCE_SIDE_ONLY_PAIRS,
 (SELECT COUNT(DISTINCT LEVEL_ID) FROM reverse_raw)
    AS DISTINCT_REFERENCED_LEVEL_IDS
"""
result = read(sql)[0]
print(json.dumps(result, indent=2, default=str))
good = (
    result["TOPICS_WITH_ONE_PARENT_ID"] == result["DISTINCT_TOPICS"]
    and result["TOPICS_WITH_MULTIPLE_PARENT_IDS"] == 0
    and result["TOPICS_WITHOUT_PARENT_ID"] == 0
    and result["TOPIC_PARENT_IDS_NOT_FOUND"] == 0
    and result["TOPIC_SIDE_ONLY_PAIRS"] == 0
    and result["SOURCE_SIDE_ONLY_PAIRS"] == 0
    and result["RECIPROCAL_PAIRS"] == result["TOPIC_SIDE_DISTINCT_PAIRS"]
    and result["RECIPROCAL_PAIRS"] == result["SOURCE_SIDE_DISTINCT_PAIRS"]
)
print("PARENT_REFERENCE_RECIPROCITY:", "PASS" if good else "REVIEW_REQUIRED")
print("This validates source references, NOT a persisted OSCAL parent edge.")
print("DONE: no mapper execution, registry update or target writes.")
