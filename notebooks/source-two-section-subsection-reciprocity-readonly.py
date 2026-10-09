# %% Source Two: Section and Sub-Section reciprocal lineage QA
# 2026-10-09. READ ONLY. Run as ONE new Python cell after mapper Cell 1.
# This is NOT a Catalog mapper PREVIEW, registry setup, or database load.
# It uses existing Source Two RAW metadata and prints aggregated counts only.

import json
import re

if "session" not in globals() or "SOURCE_FILES" not in globals():
    raise RuntimeError("Load the mapper's existing Cell 1 first; do not run all mapper cells.")

profiles = [p for p in SOURCE_FILES if p.get("SOURCE_KEY") == "source-two-source"
            and "CATALOG" in p.get("MODEL_BINDINGS", ())]
if len(profiles) != 1:
    raise RuntimeError("Expected exactly one configured Authoritative Source Catalog profile.")

source_name = profiles[0]["RAW_TABLE"]
ident = re.compile(r"^[A-Z_][A-Z0-9_$]*$", re.I)
parts = source_name.split(".")
if len(parts) != 3 or not all(ident.fullmatch(p) for p in parts):
    raise RuntimeError("The configured Source Two RAW table name is not a safe three-part identifier.")
database, schema, source_base = parts
if not source_base.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Source Two Source RAW naming convention must be inspected.")

def sql_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def query(sql):
    return [r.as_dict(recursive=True) for r in session.sql(sql).collect()]

# Use actual Snowflake metadata, not assumed Section/Sub-Section table names.
metadata = query(f"""
SELECT TABLE_NAME
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = {sql_quote(schema.upper())}
  AND TABLE_NAME ILIKE '%RAW'
ORDER BY TABLE_NAME
""")
tables = [str(r["TABLE_NAME"]) for r in metadata]
if not all(ident.fullmatch(name) for name in tables):
    raise RuntimeError("Unexpected table identifier from information schema.")
stem = source_base[:-len("_SOURCE_RAW")].upper()

def same_source_family(candidate_prefix):
    # Some Archer child tables omit an intermediate token used in the Source
    # table name. Derive parentage from the configured Source profile instead
    # of hard-coding a client/application name or guessing a child table.
    source_tokens, candidate_tokens = stem.split("_"), candidate_prefix.split("_")
    if not source_tokens or not candidate_tokens or source_tokens[0] != candidate_tokens[0]:
        return False
    shared_trailing_tokens = 0
    for left, right in zip(reversed(source_tokens), reversed(candidate_tokens)):
        if left != right:
            break
        shared_trailing_tokens += 1
    return shared_trailing_tokens >= 2

def choose_table(kind):
    candidates = []
    for name in tables:
        upper = name.upper()
        if kind == "TOPIC":
            matched = upper == stem + "_TOPIC_RAW"
        elif kind == "SECTION":
            matched = upper.endswith("_SECTION_RAW") and "SUB_SECTION" not in upper
            matched = matched and upper == stem + "_SECTION_RAW"
        elif kind == "SUB_SECTION":
            suffix = next((part for part in ("_SUB_SECTION_RAW", "_SUBSECTION_RAW")
                           if upper.endswith(part)), None)
            matched = bool(suffix and same_source_family(upper[:-len(suffix)]))
        else:
            raise ValueError("Unsupported hierarchy level")
        if matched:
            candidates.append(name)
    if len(candidates) != 1:
        print(json.dumps({"LEVEL": kind, "CANDIDATES": candidates}, default=str))
        raise RuntimeError("Ambiguous or missing RAW level; inspect the table list, do not guess.")
    return f"{database}.{schema}.{candidates[0]}"

topic = choose_table("TOPIC")
section = choose_table("SECTION")
subsection = choose_table("SUB_SECTION")

for table in (topic, section, subsection):
    columns = {str(c).strip('"').upper() for c in session.table(table).columns}
    if not {"CONTENT_ID", "CURATED_JSON"} <= columns:
        raise RuntimeError("Required CONTENT_ID / CURATED_JSON columns are missing.")

def parent_child_report(parent_table, child_table, parent_array, child_array, label):
    # Screenshots establish parent arrays of {ContentId, LevelId} objects and
    # child arrays of integer parent IDs. Do not treat procedure/policy arrays
    # as hierarchy; do not infer a parent from a title or tracking ID.
    for field in (parent_array, child_array):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", field):
            raise RuntimeError("Unsupported curated reference key.")

    sql = f"""
WITH parent_ids AS (
    SELECT CONTENT_ID::VARCHAR AS PID FROM {parent_table}
),
child_ids AS (
    SELECT CONTENT_ID::VARCHAR AS CID FROM {child_table}
),
forward_items AS (
    SELECT p.CONTENT_ID::VARCHAR AS PID,
           f.VALUE:"ContentId"::VARCHAR AS CID,
           f.VALUE:"LevelId"::VARCHAR AS LEVEL_ID,
           TYPEOF(f.VALUE) AS VALUE_TYPE
    FROM {parent_table} p,
         LATERAL FLATTEN(INPUT => GET(p.CURATED_JSON, {sql_quote(parent_array)})) f
),
reverse_items AS (
    SELECT c.CONTENT_ID::VARCHAR AS CID,
           f.VALUE::VARCHAR AS PID,
           TYPEOF(f.VALUE) AS VALUE_TYPE
    FROM {child_table} c,
         LATERAL FLATTEN(INPUT => GET(c.CURATED_JSON, {sql_quote(child_array)})) f
),
fwd AS (
    SELECT DISTINCT PID,CID FROM forward_items WHERE PID IS NOT NULL AND CID IS NOT NULL
),
rev AS (
    SELECT DISTINCT PID,CID FROM reverse_items WHERE PID IS NOT NULL AND CID IS NOT NULL
),
child_parents AS (
    SELECT CID, COUNT(DISTINCT PID) AS N FROM rev GROUP BY CID
)
SELECT
    (SELECT COUNT(*) FROM parent_ids) AS PARENT_ROWS,
    (SELECT COUNT(DISTINCT PID) FROM parent_ids) AS DISTINCT_PARENT_IDS,
    (SELECT COUNT(*) FROM child_ids) AS CHILD_ROWS,
    (SELECT COUNT(DISTINCT CID) FROM child_ids) AS DISTINCT_CHILD_IDS,
    (SELECT COUNT(*) FROM forward_items) AS PARENT_TO_CHILD_ITEMS,
    (SELECT COUNT(*) FROM reverse_items) AS CHILD_TO_PARENT_ITEMS,
    (SELECT COALESCE(COUNT_IF(VALUE_TYPE <> 'OBJECT' OR CID IS NULL),0)
      FROM forward_items) AS MALFORMED_PARENT_REFERENCE_ITEMS,
    (SELECT COALESCE(COUNT_IF(VALUE_TYPE <> 'INTEGER' OR PID IS NULL),0)
      FROM reverse_items) AS MALFORMED_CHILD_REFERENCE_ITEMS,
    (SELECT COUNT(DISTINCT LEVEL_ID) FROM forward_items WHERE LEVEL_ID IS NOT NULL)
      AS DISTINCT_CHILD_LEVEL_IDS,
    (SELECT MIN(LEVEL_ID) FROM forward_items WHERE LEVEL_ID IS NOT NULL)
      AS MIN_CHILD_LEVEL_ID,
    (SELECT MAX(LEVEL_ID) FROM forward_items WHERE LEVEL_ID IS NOT NULL)
      AS MAX_CHILD_LEVEL_ID,
    (SELECT COUNT(*) FROM fwd) AS PARENT_SIDE_PAIRS,
    (SELECT COUNT(*) FROM rev) AS CHILD_SIDE_PAIRS,
    (SELECT COUNT(*) FROM fwd f JOIN rev r ON f.PID=r.PID AND f.CID=r.CID)
      AS RECIPROCAL_PAIRS,
    (SELECT COUNT(*) FROM fwd f
      WHERE NOT EXISTS(SELECT 1 FROM rev r WHERE r.PID=f.PID AND r.CID=f.CID))
      AS PARENT_ONLY_PAIRS,
    (SELECT COUNT(*) FROM rev r
      WHERE NOT EXISTS(SELECT 1 FROM fwd f WHERE f.PID=r.PID AND f.CID=r.CID))
      AS CHILD_ONLY_PAIRS,
    (SELECT COUNT(*) FROM fwd f
      LEFT JOIN child_ids c ON c.CID=f.CID WHERE c.CID IS NULL)
      AS MISSING_CHILD_RECORD_PAIRS,
    (SELECT COUNT(*) FROM rev r
      LEFT JOIN parent_ids p ON p.PID=r.PID WHERE p.PID IS NULL)
      AS MISSING_PARENT_RECORD_PAIRS,
    (SELECT COUNT(*) FROM child_parents WHERE N > 1) AS CHILDREN_WITH_MULTIPLE_PARENTS,
    (SELECT COUNT(*) FROM child_ids c
      WHERE NOT EXISTS(SELECT 1 FROM rev r WHERE r.CID=c.CID))
      AS CHILDREN_WITHOUT_PARENTS
"""
    row = query(sql)[0]
    reasons = []
    if row["PARENT_ROWS"] != row["DISTINCT_PARENT_IDS"]:
        reasons.append("DUPLICATE_OR_NULL_PARENT_CONTENT_IDS")
    if row["CHILD_ROWS"] != row["DISTINCT_CHILD_IDS"]:
        reasons.append("DUPLICATE_OR_NULL_CHILD_CONTENT_IDS")
    for field in (
        "MALFORMED_PARENT_REFERENCE_ITEMS", "MALFORMED_CHILD_REFERENCE_ITEMS",
        "PARENT_ONLY_PAIRS", "CHILD_ONLY_PAIRS",
        "MISSING_CHILD_RECORD_PAIRS", "MISSING_PARENT_RECORD_PAIRS",
        "CHILDREN_WITH_MULTIPLE_PARENTS", "CHILDREN_WITHOUT_PARENTS",
    ):
        if row[field] != 0:
            reasons.append(field)
    if row["PARENT_SIDE_PAIRS"] != row["RECIPROCAL_PAIRS"] or (
        row["CHILD_SIDE_PAIRS"] != row["RECIPROCAL_PAIRS"]
    ):
        reasons.append("RECIPROCITY_COUNTS_DIFFER")
    if row["CHILD_TO_PARENT_ITEMS"] != row["CHILD_SIDE_PAIRS"]:
        reasons.append("REPEATED_CHILD_PARENT_REFERENCE_ITEMS")
    if row["PARENT_TO_CHILD_ITEMS"] != row["PARENT_SIDE_PAIRS"]:
        reasons.append("REPEATED_PARENT_CHILD_REFERENCE_ITEMS")
    if row["CHILD_ROWS"] == 0:
        reasons.append("EMPTY_CHILD_SOURCE")
    print(json.dumps({"RELATION": label, "STATUS": "PASS" if not reasons else "REVIEW_REQUIRED",
                      "ISSUES": reasons, "COUNTS": row}, indent=2, default=str))
    return not reasons

print("SOURCE TWO HIERARCHY: OWNER READ-ONLY RECIPROCITY")
print(json.dumps({"TOPIC_RAW": topic, "SECTION_RAW": section,
                  "SUB_SECTION_RAW": subsection}, indent=2))
first = parent_child_report(topic, section, "SECTION_REFERENCES",
                            "TOPIC_REFERENCES", "TOPIC -> SECTION")
second = parent_child_report(section, subsection, "SUB_SECTION_REFERENCES",
                             "SECTION_REFERENCES", "SECTION -> SUB-SECTION")
print("HIERARCHY_READINESS:", "PASS" if first and second else "REVIEW_REQUIRED")
print("This checks Archer source relationships, NOT OSCAL DIM/FACT or UCF links.")
print("DONE: SELECT-only. No mapper PREVIEW, registry update, or data writes.")
