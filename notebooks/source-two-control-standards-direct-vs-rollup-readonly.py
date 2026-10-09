# %% Source Two Control Standards: direct vs descendant-reference contract
# Read-only: one new Python cell in the existing Source Two notebook.
# Uses existing session, SOURCE_FILES and previously resolved hierarchy tables.
# Does not build OSCAL controls; do not execute catalog registry or mapper writes.

import json
import re

if any(name not in globals() for name in ("session", "SOURCE_FILES", "topic", "section", "subsection")):
    raise RuntimeError("Use the notebook with Source Two Cell 1 and prior hierarchy bindings.")

profiles = [p for p in SOURCE_FILES
            if p.get("SOURCE_KEY") == "source-two-source"
            and "CATALOG" in p.get("MODEL_BINDINGS", ())]
if len(profiles) != 1:
    raise RuntimeError("Expected exactly one Source Two authoritative source profile.")

safe_name = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

def identifier(name):
    parts = str(name).split(".")
    if len(parts) != 3 or not all(safe_name.fullmatch(part) for part in parts):
        raise ValueError("Unverified three-part Source Two RAW table identifier")
    return tuple(parts)

source_parts = identifier(profiles[0]["RAW_TABLE"])
level_tables = [
    ("SOURCE", source_parts),
    ("TOPIC", identifier(topic)),
    ("SECTION", identifier(section)),
    ("SUB_SECTION", identifier(subsection)),
]
if any(parts[:2] != source_parts[:2] for _, parts in level_tables):
    raise RuntimeError("The four Source Two levels must share one RAW namespace.")
if len({parts for _, parts in level_tables}) != 4:
    raise RuntimeError("Each Source Two hierarchy level requires a distinct table.")

def quoted(parts):
    return ".".join('"' + part + '"' for part in parts)

# Explicit source fields from the reviewed Authoritative Sources worksheets.
# ROLLUP is diagnostic only: never create duplicate native controls from it.
direct_field = "CONTROL_STANDARDS"
rollup_fields = {
    "SOURCE": "CONTROL_STANDARDS_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS",
    "TOPIC": "CONTROL_STANDARDS_FROM_SECTION_AND_SUBSECTION_LEVELS",
    "SECTION": "CONTROL_STANDARDS_FROM_SECTION_LEVEL_AND_BELOW",
}

rows_sql = []
for level, path in level_tables:
    fqtn = quoted(path)
    rows_sql.append(
        "SELECT '" + level + "' AS HIERARCHY_LEVEL, 'DIRECT' AS REFERENCE_KIND, "
        "CONTENT_ID::VARCHAR AS SOURCE_RECORD_ID, "
        "GET(CURATED_JSON, '" + direct_field + "') AS REFERENCES_VALUE "
        "FROM " + fqtn
    )
    if level in rollup_fields:
        rows_sql.append(
            "SELECT '" + level + "' AS HIERARCHY_LEVEL, 'ROLLUP' AS REFERENCE_KIND, "
            "CONTENT_ID::VARCHAR AS SOURCE_RECORD_ID, "
            "GET(CURATED_JSON, '" + rollup_fields[level] + "') AS REFERENCES_VALUE "
            "FROM " + fqtn
        )

cte = "WITH reviewed_fields AS (\n" + "\nUNION ALL\n".join(rows_sql) + "\n)\n"
distribution_sql = cte + """
SELECT HIERARCHY_LEVEL, REFERENCE_KIND,
       COUNT(*) AS SOURCE_RECORDS,
       COALESCE(COUNT_IF(REFERENCES_VALUE IS NULL OR
                         IS_NULL_VALUE(REFERENCES_VALUE)), 0) AS MISSING_OR_NULL,
       COALESCE(COUNT_IF(TYPEOF(REFERENCES_VALUE) = 'ARRAY'), 0) AS ARRAY_RECORDS,
       COALESCE(COUNT_IF(TYPEOF(REFERENCES_VALUE) = 'OBJECT'), 0) AS OBJECT_RECORDS,
       COALESCE(COUNT_IF(TYPEOF(REFERENCES_VALUE) NOT IN
                         ('ARRAY', 'OBJECT', 'NULL_VALUE') AND
                         REFERENCES_VALUE IS NOT NULL), 0) AS SCALAR_RECORDS,
       COALESCE(COUNT_IF(TYPEOF(REFERENCES_VALUE) = 'ARRAY' AND
                         ARRAY_SIZE(REFERENCES_VALUE) > 0), 0) AS NONEMPTY_ARRAYS
FROM reviewed_fields
GROUP BY HIERARCHY_LEVEL, REFERENCE_KIND
ORDER BY HIERARCHY_LEVEL, REFERENCE_KIND
"""

shape_sql = cte + """,
items AS (
  SELECT r.HIERARCHY_LEVEL, r.REFERENCE_KIND, r.SOURCE_RECORD_ID,
         f.VALUE AS ITEM
  FROM reviewed_fields r,
       LATERAL FLATTEN(
           INPUT => CASE
               WHEN IS_ARRAY(r.REFERENCES_VALUE) THEN r.REFERENCES_VALUE
               WHEN r.REFERENCES_VALUE IS NULL OR
                    IS_NULL_VALUE(r.REFERENCES_VALUE) THEN ARRAY_CONSTRUCT()
               ELSE ARRAY_CONSTRUCT(r.REFERENCES_VALUE)
           END
       ) f
)
SELECT HIERARCHY_LEVEL, REFERENCE_KIND,
       TYPEOF(ITEM) AS ITEM_TYPE,
       CASE WHEN IS_OBJECT(ITEM)
            THEN ARRAY_TO_STRING(ARRAY_SORT(OBJECT_KEYS(ITEM)), ',')
            ELSE NULL END AS OBJECT_KEY_SHAPE,
       COUNT(*) AS ITEM_COUNT,
       COUNT(DISTINCT SOURCE_RECORD_ID) AS RECORDS_WITH_THIS_SHAPE
FROM items
GROUP BY HIERARCHY_LEVEL, REFERENCE_KIND, ITEM_TYPE, OBJECT_KEY_SHAPE
ORDER BY HIERARCHY_LEVEL, REFERENCE_KIND, ITEM_COUNT DESC
"""

def collect(sql):
    return [row.as_dict(recursive=True) for row in session.sql(sql).collect()]

distribution = collect(distribution_sql)
shapes = collect(shape_sql)
expected_pairs = {(level, kind)
                  for level, _ in level_tables
                  for kind in (("DIRECT", "ROLLUP") if level in rollup_fields
                               else ("DIRECT",))}
actual_pairs = {(row["HIERARCHY_LEVEL"], row["REFERENCE_KIND"])
                for row in distribution}
if actual_pairs != expected_pairs:
    raise RuntimeError("The direct/rollup field inventory is incomplete or duplicated.")
if any(row["SOURCE_RECORDS"] < 1 for row in distribution):
    raise RuntimeError("An expected Authoritative Sources hierarchy table is empty.")

print("SOURCE TWO: CONTROL STANDARD DIRECT/ROLLUP SOURCE FIELD PROFILE")
print(json.dumps({
    "DIRECT_VS_ROLLUP_COUNTS": distribution,
    "REFERENCE_ITEM_SHAPES": shapes,
    "MAPPED_CONTROL_STATUS": "NOT_YET_APPROVED_OR_LOADED",
}, indent=2, default=str))
print("Do not infer control IDs, titles or native OSCAL controls from these shapes alone.")
print("A rollup source field is not a second direct-control ownership relationship.")
print("DONE: two aggregate SELECTs; no source, registry, DIM/FACT or mapper writes.")
