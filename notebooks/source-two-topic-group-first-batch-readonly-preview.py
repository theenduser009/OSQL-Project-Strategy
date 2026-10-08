# Source Two: preview first OSCAL Catalog Topic groups WITHOUT modifying the mapper.
# One Python cell in the already-loaded Snowflake notebook, after Cell 1.
# Derives table and original field names from the existing Source profile.
# All outputs are SOURCE CANDIDATES; no DIM/FACT/registry DML or COMMIT.

import json
import re

if not all(k in globals() for k in ("session", "SOURCE_FILES", "MODEL_CONTRACTS")):
    raise RuntimeError("Use the current mapper notebook with Cell 1 loaded.")

profiles = [p for p in SOURCE_FILES
            if "CATALOG" in p.get("MODEL_BINDINGS", ()) and p.get("RAW_TABLE")]
if len(profiles) != 1:
    raise RuntimeError("Expected one configured Catalog Source profile.")
profile = profiles[0]
storage = MODEL_CONTRACTS["CATALOG"]["STORAGE_CONTRACT"]

def object_name(text):
    text = str(text)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*){0,2}", text):
        raise RuntimeError("Unexpected configured Snowflake identifier.")
    return text

def lit(text):
    return "'" + str(text).replace("'", "''") + "'"

src = object_name(profile["RAW_TABLE"])
dim = object_name(storage["TARGET_DIM"])
db, schema, base = src.split(".")
if not base.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Unexpected configured Source RAW table suffix.")
topic_basename = base[:-len("_SOURCE_RAW")] + "_TOPIC_RAW"
topic = object_name(f"{db}.{schema}.{topic_basename}")
entity = topic_basename[:-len("_RAW")].split("_")[-1].upper()
fields = {
    "title": entity + "_NAME",
    "id": entity + "_ID",
    "tracking": entity + "_TRACKING_ID"
}
rows = lambda sql: [r.as_dict() for r in session.sql(sql).collect()]
keys = set(r["NAME"] for r in rows(f"""
SELECT DISTINCT f.KEY::VARCHAR AS NAME
FROM {topic} t, LATERAL FLATTEN(INPUT=>t.CURATED_JSON) f
WHERE f.KEY IS NOT NULL
"""))
parents = [s for s in keys if "SOURCE" in s.upper() and "REF" in s.upper()]
print("SOURCE TWO TOPIC GROUP — FIELD MAPPING PREVIEW")
print("Resolved source keys:", json.dumps(fields))
if any(v not in keys for v in fields.values()) or len(parents) != 1:
    raise RuntimeError("Missing Topic identity/title/tracking or ambiguous Source parent field.")

base_sql = f"""
WITH parent_catalog AS (
  SELECT SOURCE_RECORD_ID::VARCHAR AS PARENT_SOURCE_ID,
         COUNT(*) AS ROOT_COUNT, MAX(OSCAL_UUID) AS ROOT_UUID
  FROM {dim}
  WHERE SOURCE_SYSTEM_NAME={lit(profile['SOURCE_SYSTEM_NAME'])}
    AND SOURCE_TABLE_NAME={lit(profile['SOURCE_TABLE_NAME'])}
    AND ELEMENT_TYPE='catalog'
  GROUP BY SOURCE_RECORD_ID
), candidate AS (
  SELECT CONTENT_ID::VARCHAR AS RECORD_ID,
         GET(CURATED_JSON,{lit(fields['title'])})::VARCHAR AS GROUP_TITLE,
         GET(CURATED_JSON,{lit(fields['id'])})::VARCHAR AS GROUP_ID,
         GET(CURATED_JSON,{lit(fields['tracking'])})::VARCHAR AS TRACKING,
         TYPEOF(GET(CURATED_JSON,{lit(fields['title'])})) AS TITLE_TYPE,
         TYPEOF(GET(CURATED_JSON,{lit(fields['id'])})) AS ID_TYPE,
         TYPEOF(GET(CURATED_JSON,{lit(fields['tracking'])})) AS TRACK_TYPE,
         GET(GET(CURATED_JSON,{lit(parents[0])}),0)::VARCHAR AS PARENT_SOURCE_ID
  FROM {topic}
), assembled AS (
  SELECT c.*,p.ROOT_COUNT,p.ROOT_UUID
  FROM candidate c LEFT JOIN parent_catalog p
    ON p.PARENT_SOURCE_ID=c.PARENT_SOURCE_ID
)
"""
summary = rows(base_sql + """
SELECT
  COUNT(*) AS TOPIC_RECORDS,
  COUNT(DISTINCT RECORD_ID) AS DISTINCT_RECORD_IDS,
  COALESCE(COUNT_IF(GROUP_TITLE IS NULL OR TRIM(GROUP_TITLE)=''),0) AS MISSING_TITLE,
  COALESCE(COUNT_IF(GROUP_TITLE IS NOT NULL AND TITLE_TYPE<>'VARCHAR'),0) AS NON_TEXT_TITLES,
  COALESCE(COUNT_IF(GROUP_ID IS NULL OR TRIM(GROUP_ID)=''),0) AS MISSING_GROUP_ID,
  COUNT(DISTINCT NULLIF(TRIM(GROUP_ID),'')) AS DISTINCT_GROUP_IDS,
  COALESCE(COUNT_IF(GROUP_ID IS NOT NULL AND
    NOT REGEXP_LIKE(GROUP_ID,'^[A-Za-z_][A-Za-z0-9_.-]*$')),0)
    AS GROUP_IDS_NEEDING_TOKEN_REVIEW,
  COALESCE(COUNT_IF(TRACKING IS NULL OR TRIM(TRACKING)=''),0) AS MISSING_TRACKING,
  COALESCE(COUNT_IF(PARENT_SOURCE_ID IS NULL),0) AS MISSING_PARENT_SOURCE_ID,
  COALESCE(COUNT_IF(ROOT_COUNT IS NULL),0) AS MISSING_PERSISTED_CATALOG_PARENT,
  COALESCE(COUNT_IF(ROOT_COUNT>1),0) AS AMBIGUOUS_PERSISTED_CATALOG_PARENT,
  COUNT(DISTINCT IFF(ROOT_COUNT=1,PARENT_SOURCE_ID,NULL))
    AS DISTINCT_PERSISTED_CATALOG_PARENTS
FROM assembled
""")[0]
print("READ-ONLY CANDIDATE MAPPING COVERAGE")
print(json.dumps(summary, indent=2, default=str))

preview = rows(base_sql + """
SELECT RECORD_ID, GROUP_ID, GROUP_TITLE, TRACKING, TITLE_TYPE, ID_TYPE,
       TRACK_TYPE, PARENT_SOURCE_ID, ROOT_UUID
FROM assembled
ORDER BY RECORD_ID
LIMIT 5
""")
print("CANDIDATE CATALOG GROUPS (no new node hashes or FACT edges)")
for r in preview:
    print(json.dumps({
        "source_record_id": r["RECORD_ID"],
        "source_parent_id": r["PARENT_SOURCE_ID"],
        "persisted_source_catalog_uuid": r["ROOT_UUID"],
        "candidate_group": {
            "id": r["GROUP_ID"],
            "title": r["GROUP_TITLE"],
            "props": ([{"name": "tracking-id", "value": r["TRACKING"]}]
                      if r["TRACKING"] not in (None, "") else [])
        },
        "source_types": {"id": r["ID_TYPE"], "title": r["TITLE_TYPE"],
                         "tracking": r["TRACK_TYPE"]}
    }, ensure_ascii=False, default=str))
print("NEXT: validate identity token and implement generic cross-record parents in PREVIEW.")
print("DONE: SELECT only; no mapper, registry, Source Catalog or Topic DML.")
