# %% Source Two: inspect unmatched Section -> Sub-Section references
# READ ONLY: one Python cell in the SAME Snowflake notebook after the
# Source Two hierarchy reciprocity check. No new inputs or target writes.
# This is source data profiling, NOT an OSCAL Catalog mapper PREVIEW.
import json
import re

if not all(k in globals() for k in ("session", "section", "subsection")):
    raise RuntimeError(
        "Run the earlier read-only Source Two hierarchy check in this notebook first."
    )

def safe_table(value):
    parts = str(value).split(".")
    pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
    if len(parts) != 3 or not all(pattern.fullmatch(p) for p in parts):
        raise RuntimeError("Unexpected table identifier from the earlier read-only check")
    return parts

sec_parts = safe_table(section)
sub_parts = safe_table(subsection)
if sec_parts[:2] != sub_parts[:2]:
    raise RuntimeError("Section and Sub-Section must use the same configured RAW namespace")
database, schema = sec_parts[:2]
section_table = ".".join(sec_parts)
subsection_table = ".".join(sub_parts)

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def read(sql):
    return [r.as_dict(recursive=True) for r in session.sql(sql).collect()]

# Parent field and child record identity were established by the preceding
# owner-run hierarchy check. Keep the raw source reference shape intact.
missing_cte = f"""
WITH parent_refs AS (
    SELECT s.CONTENT_ID::VARCHAR AS SECTION_ID,
           f.VALUE:"ContentId"::VARCHAR AS REFERENCED_SUB_SECTION_ID,
           f.VALUE:"LevelId"::VARCHAR AS CHILD_LEVEL_ID
    FROM {section_table} s,
         LATERAL FLATTEN(
             INPUT => GET(s.CURATED_JSON, 'SUB_SECTION_REFERENCES')
         ) f
),
sub_section_ids AS (
    SELECT DISTINCT CONTENT_ID::VARCHAR AS CHILD_ID
    FROM {subsection_table}
    WHERE CONTENT_ID IS NOT NULL
),
unmatched AS (
    SELECT p.SECTION_ID,
           p.REFERENCED_SUB_SECTION_ID,
           p.CHILD_LEVEL_ID
    FROM parent_refs p
    LEFT JOIN sub_section_ids c
      ON c.CHILD_ID = p.REFERENCED_SUB_SECTION_ID
    WHERE c.CHILD_ID IS NULL
)
"""

overview = read(missing_cte + """
SELECT COUNT(*) AS UNMATCHED_PARENT_REFERENCE_ITEMS,
       COUNT(DISTINCT REFERENCED_SUB_SECTION_ID) AS DISTINCT_MISSING_CHILD_IDS,
       COUNT(DISTINCT SECTION_ID) AS AFFECTED_SECTIONS,
       COALESCE(COUNT_IF(REFERENCED_SUB_SECTION_ID IS NULL), 0)
           AS MISSING_CHILD_ID_VALUES,
       COALESCE(COUNT_IF(CHILD_LEVEL_ID IS NULL), 0)
           AS MISSING_LEVEL_ID_VALUES,
       COUNT(DISTINCT CHILD_LEVEL_ID) AS DISTINCT_CHILD_LEVEL_IDS,
       MIN(CHILD_LEVEL_ID) AS MIN_LEVEL_ID,
       MAX(CHILD_LEVEL_ID) AS MAX_LEVEL_ID
FROM unmatched
""")[0]

duplicate_linkage = read(missing_cte + """
SELECT COUNT(*) AS MISSING_IDS_REFERENCED_BY_MULTIPLE_SECTIONS
FROM (
    SELECT REFERENCED_SUB_SECTION_ID
    FROM unmatched
    WHERE REFERENCED_SUB_SECTION_ID IS NOT NULL
    GROUP BY REFERENCED_SUB_SECTION_ID
    HAVING COUNT(DISTINCT SECTION_ID) > 1
)
""")[0]

print("SECTION -> SUB-SECTION: UNMATCHED PARENT-REFERENCE DIAGNOSTIC")
print(json.dumps({"SUMMARY": overview, "DUPLICATE_PARENT_CHECK": duplicate_linkage},
                 indent=2, default=str))

# Identify the highest-contributing parent Sections. Content IDs are printed
# ONLY in this owner's Snowflake notebook, never stored in public GitHub.
parents = read(missing_cte + """
SELECT SECTION_ID, COUNT(*) AS MISSING_REFERENCE_ITEMS
FROM unmatched
GROUP BY SECTION_ID
ORDER BY MISSING_REFERENCE_ITEMS DESC, SECTION_ID
LIMIT 10
""")
samples = read(missing_cte + """
SELECT SECTION_ID, REFERENCED_SUB_SECTION_ID, CHILD_LEVEL_ID
FROM unmatched
ORDER BY SECTION_ID, REFERENCED_SUB_SECTION_ID
LIMIT 10
""")
print("AFFECTED_SECTIONS_SAMPLE (internal notebook only):")
print(json.dumps(parents, indent=2, default=str))
print("UNMATCHED_REFS_SAMPLE (internal notebook only):")
print(json.dumps(samples, indent=2, default=str))

# Optional exact same-family base/STG tables may contain the missing IDs.
# These are diagnostic snapshots, NOT authoritative replacements for RAW.
raw_name = sub_parts[2]
if not raw_name.upper().endswith("_RAW"):
    raise RuntimeError("Sub-Section table suffix requires manual review")
stem = raw_name[:-len("_RAW")]
candidate_names = (stem, stem + "_STG")
available = read(f"""
SELECT TABLE_NAME
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = {quote(schema.upper())}
  AND TABLE_NAME IN ({", ".join(quote(x.upper()) for x in candidate_names)})
""")
present = {str(row["TABLE_NAME"]).upper() for row in available}
alternative_results = []
for name in candidate_names:
    if name.upper() not in present:
        alternative_results.append({"TABLE_ROLE": "BASE" if name == stem else "STG",
                                    "STATUS": "NOT_PRESENT"})
        continue
    candidate = f"{database}.{schema}.{name}"
    columns = {str(c).strip('"').upper() for c in session.table(candidate).columns}
    if "CONTENT_ID" not in columns:
        alternative_results.append({"TABLE_ROLE": "BASE" if name == stem else "STG",
                                    "STATUS": "MISSING_CONTENT_ID_COLUMN"})
        continue
    record = read(missing_cte + f"""
SELECT COUNT(DISTINCT u.REFERENCED_SUB_SECTION_ID) AS
           MISSING_RAW_IDS_FOUND_IN_ALTERNATIVE
FROM unmatched u
JOIN {candidate} other
  ON other.CONTENT_ID::VARCHAR = u.REFERENCED_SUB_SECTION_ID
""")[0]
    alternative_results.append({
        "TABLE_ROLE": "BASE" if name == stem else "STG",
        "STATUS": "CHECKED",
        **record,
    })
print("ALTERNATIVE_SOURCE_COVERAGE (informational; never substitute for RAW):")
print(json.dumps(alternative_results, indent=2, default=str))

if overview["UNMATCHED_PARENT_REFERENCE_ITEMS"] == 0:
    print("UNMATCHED_REFERENCE_STATUS: NONE_IN_CURRENT_SNAPSHOT")
else:
    print("UNMATCHED_REFERENCE_STATUS: REVIEW_REQUIRED")
print("No records were fabricated, deleted, excluded, or mapped.")
print("DONE: SELECT-only source diagnostic; no registry, DIM/FACT or mapper writes.")
