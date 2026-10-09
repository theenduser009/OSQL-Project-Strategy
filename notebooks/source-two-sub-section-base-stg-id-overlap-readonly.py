# %% Source Two: reconcile missing Sub-Section RAW Content IDs with BASE/STG
# One SELECT-only Python cell after the existing hierarchy inspector.
# Uses actual physical content-ID column discovered in INFORMATION_SCHEMA.
# This measures identity overlap; it does not approve keys or repair data.

import json
import re

if not all(name in globals() for name in ("session", "section", "subsection")):
    raise RuntimeError("Use the same notebook session as the read-only hierarchy check.")

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

def parts(value):
    chunks = str(value).split(".")
    if len(chunks) != 3 or not all(_SAFE.fullmatch(chunk) for chunk in chunks):
        raise RuntimeError("A prior source table name needs review.")
    return chunks

def ident(value):
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise RuntimeError("Unverified physical identifier; no SQL executed.")
    return '"' + value.replace('"', '""') + '"'

def literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def fetch_one(sql):
    rows = session.sql(sql).collect()
    if len(rows) != 1:
        raise RuntimeError("Expected exactly one aggregate result.")
    return rows[0].as_dict(recursive=True)

sec = parts(section)
sub = parts(subsection)
if sec[:2] != sub[:2] or not sub[2].upper().endswith("_RAW"):
    raise RuntimeError("Section/Sub-Section RAW namespace or table naming differs.")

db, schema, raw_name = sub
stem = raw_name[:-len("_RAW")]
if not stem.upper().endswith("_SUB_SECTION"):
    raise RuntimeError("Sub-Section source family needs review.")
expected_parent = stem[:-len("_SUB_SECTION")] + "_SECTION_RAW"
if sec[2].upper() != expected_parent.upper():
    raise RuntimeError("Section/Sub-Section source family does not match.")
base_name, stg_name = stem, stem + "_STG"
expected_identity = stem + "_CONTENT_ID"

def table(name):
    return ".".join(ident(x) for x in (db, schema, name))

# Current screenshot-backed expectation is one uniquely named numeric-like
# <SubSectionStem>_Content_ID physical column per BASE/STG table.
# Resolve its exact mixed-case spelling; never use Tracking ID or business ID.
meta_sql = f"""
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM {ident(db)}.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = {literal(schema.upper())}
  AND TABLE_NAME IN ({literal(base_name.upper())}, {literal(stg_name.upper())})
  AND UPPER(COLUMN_NAME) = {literal(expected_identity.upper())}
ORDER BY TABLE_NAME, COLUMN_NAME
"""
meta = [row.as_dict(recursive=True) for row in session.sql(meta_sql).collect()]
cols = {}
for logical, name in (("BASE", base_name), ("STG", stg_name)):
    found = [row for row in meta if str(row["TABLE_NAME"]).upper() == name.upper()]
    if len(found) != 1:
        raise RuntimeError("Required BASE/STG physical Content ID candidate is missing or ambiguous: " + logical)
    column = str(found[0]["COLUMN_NAME"])
    datatype = str(found[0]["DATA_TYPE"]).upper()
    if datatype not in {"NUMBER", "DECIMAL", "NUMERIC", "TEXT", "VARCHAR"}:
        raise RuntimeError("Content ID candidate type needs review for " + logical)
    cols[logical] = {"column": column, "datatype": datatype,
                     "nullable": found[0]["IS_NULLABLE"]}

base_id = ident(cols["BASE"]["column"])
stg_id = ident(cols["STG"]["column"])
sql = f"""
WITH raw_records AS (
    SELECT NULLIF(TRIM(CONTENT_ID::VARCHAR), '') AS CHILD_ID
    FROM {table(raw_name)}
),
raw_ids AS (
    SELECT DISTINCT CHILD_ID FROM raw_records WHERE CHILD_ID IS NOT NULL
),
section_forward AS (
    SELECT s.CONTENT_ID::VARCHAR AS SECTION_ID,
           ref.VALUE:"ContentId"::VARCHAR AS CHILD_ID
    FROM {table(sec[2])} s,
         LATERAL FLATTEN(INPUT => GET(s.CURATED_JSON, 'SUB_SECTION_REFERENCES')) ref
),
missing_refs AS (
    SELECT DISTINCT f.CHILD_ID
    FROM section_forward f LEFT JOIN raw_ids r ON r.CHILD_ID=f.CHILD_ID
    WHERE f.CHILD_ID IS NOT NULL AND r.CHILD_ID IS NULL
),
base_rows AS (
    SELECT NULLIF(TRIM({base_id}::VARCHAR), '') AS CHILD_ID
    FROM {table(base_name)}
),
stg_rows AS (
    SELECT NULLIF(TRIM({stg_id}::VARCHAR), '') AS CHILD_ID
    FROM {table(stg_name)}
),
base_ids AS (
    SELECT DISTINCT CHILD_ID FROM base_rows WHERE CHILD_ID IS NOT NULL
),
stg_ids AS (
    SELECT DISTINCT CHILD_ID FROM stg_rows WHERE CHILD_ID IS NOT NULL
)
SELECT
    (SELECT COUNT(*) FROM raw_records) AS RAW_ROWS,
    (SELECT COUNT(*) FROM raw_ids) AS RAW_DISTINCT_IDS,
    (SELECT COUNT(*) FROM section_forward) AS SECTION_FORWARD_ITEMS,
    (SELECT COUNT(*) FROM missing_refs) AS MISSING_RAW_REFERENCE_IDS,

    (SELECT COUNT(*) FROM base_rows) AS BASE_ROWS,
    (SELECT COUNT(*) FROM base_rows WHERE CHILD_ID IS NULL) AS BASE_NULL_IDS,
    (SELECT COUNT(*) FROM base_ids) AS BASE_DISTINCT_IDS,
    (SELECT COUNT(*) FROM (
        SELECT CHILD_ID FROM base_rows WHERE CHILD_ID IS NOT NULL
        GROUP BY CHILD_ID HAVING COUNT(*) > 1
    )) AS BASE_DUPLICATE_ID_GROUPS,

    (SELECT COUNT(*) FROM stg_rows) AS STG_ROWS,
    (SELECT COUNT(*) FROM stg_rows WHERE CHILD_ID IS NULL) AS STG_NULL_IDS,
    (SELECT COUNT(*) FROM stg_ids) AS STG_DISTINCT_IDS,
    (SELECT COUNT(*) FROM (
        SELECT CHILD_ID FROM stg_rows WHERE CHILD_ID IS NOT NULL
        GROUP BY CHILD_ID HAVING COUNT(*) > 1
    )) AS STG_DUPLICATE_ID_GROUPS,

    (SELECT COUNT(*) FROM raw_ids r JOIN base_ids b ON r.CHILD_ID=b.CHILD_ID)
       AS CURRENT_RAW_IDS_MATCHED_IN_BASE,
    (SELECT COUNT(*) FROM raw_ids r JOIN stg_ids g ON r.CHILD_ID=g.CHILD_ID)
       AS CURRENT_RAW_IDS_MATCHED_IN_STG,

    (SELECT COUNT(*) FROM missing_refs m
       JOIN base_ids b ON b.CHILD_ID=m.CHILD_ID)
       AS MISSING_REF_IDS_FOUND_IN_BASE,
    (SELECT COUNT(*) FROM missing_refs m
       JOIN stg_ids g ON g.CHILD_ID=m.CHILD_ID)
       AS MISSING_REF_IDS_FOUND_IN_STG,

    (SELECT COUNT(*) FROM missing_refs m
       JOIN base_ids b ON b.CHILD_ID=m.CHILD_ID
       JOIN stg_ids g ON g.CHILD_ID=m.CHILD_ID)
       AS MISSING_REF_IDS_IN_BOTH,
    (SELECT COUNT(*) FROM missing_refs m
       JOIN base_ids b ON b.CHILD_ID=m.CHILD_ID
       LEFT JOIN stg_ids g ON g.CHILD_ID=m.CHILD_ID
       WHERE g.CHILD_ID IS NULL)
       AS MISSING_REF_IDS_BASE_ONLY,
    (SELECT COUNT(*) FROM missing_refs m
       LEFT JOIN base_ids b ON b.CHILD_ID=m.CHILD_ID
       JOIN stg_ids g ON g.CHILD_ID=m.CHILD_ID
       WHERE b.CHILD_ID IS NULL)
       AS MISSING_REF_IDS_STG_ONLY,
    (SELECT COUNT(*) FROM missing_refs m
       LEFT JOIN base_ids b ON b.CHILD_ID=m.CHILD_ID
       LEFT JOIN stg_ids g ON g.CHILD_ID=m.CHILD_ID
       WHERE b.CHILD_ID IS NULL AND g.CHILD_ID IS NULL)
       AS MISSING_REF_IDS_IN_NEITHER
"""
result = fetch_one(sql)
coverage = sum(result[key] for key in (
    "MISSING_REF_IDS_IN_BOTH", "MISSING_REF_IDS_BASE_ONLY",
    "MISSING_REF_IDS_STG_ONLY", "MISSING_REF_IDS_IN_NEITHER"
))
if coverage != result["MISSING_RAW_REFERENCE_IDS"]:
    raise RuntimeError("Candidate-identity reconciliation counts do not balance.")

flags = []
for role in ("BASE", "STG"):
    if result[role + "_NULL_IDS"] or result[role + "_DUPLICATE_ID_GROUPS"]:
        flags.append(role + "_CANDIDATE_ID_NOT_UNIQUE_AND_POPULATED")
    if result["CURRENT_RAW_IDS_MATCHED_IN_" + role] != result["RAW_DISTINCT_IDS"]:
        flags.append(role + "_DOES_NOT_COVER_EVERY_CURRENT_RAW_ID")

print("SOURCE TWO SUB-SECTION: CANDIDATE ID OVERLAP WITH RAW AND MISSING REFERENCES")
print(json.dumps({
    "STATUS": "COMPUTED_FOR_SOURCE_REVIEW",
    "CANDIDATE_COLUMNS": cols,
    "IDENTITY_VALIDATION_FLAGS": flags,
    "COUNTS": result
}, indent=2, default=str))
print("SOURCE_MATCH_NOT_IDENTITY_APPROVAL: verify Archer ID lineage with the owner.")
print("BASE/STG results cannot be substituted for missing RAW rows or OSCAL nodes.")
print("DONE: 2 SELECT-only queries; no source, registry, DIM/FACT or mapper writes.")
