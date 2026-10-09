# %% Source Two Control Standards: direct versus descendant reference profile
# Self-initializing, SELECT-only Snowflake notebook Python cell.
# No dependence on previously executed hierarchy/mapper cells.
# Never writes a registry entry, OSCAL node, or source/target row.

import json
import re

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

def identifier(value):
    parts = str(value).split(".")
    if len(parts) != 3 or not all(_SAFE.fullmatch(x) for x in parts):
        raise ValueError("Expected a safely named three-part RAW table")
    return tuple(parts)

def literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def quoted(parts):
    return ".".join('"' + part + '"' for part in parts)

# A Snowflake notebook can lose Python variables when reopened or restarted.
# Obtain the active Snowpark session directly if Cell 1 was not run.
try:
    _source_two_session = session
except NameError:
    _source_two_session = None
if _source_two_session is None:
    try:
        from snowflake.snowpark.context import get_active_session
        _source_two_session = get_active_session()
    except Exception:
        raise RuntimeError(
            "No active Snowflake session. Open this cell in a connected Snowflake notebook."
        ) from None
if _source_two_session is None:
    raise RuntimeError("No active Snowflake session is available.")
session = _source_two_session

# Prefer the current mapper's Source Two profile, but do not require it.
_profiles = globals().get("SOURCE_FILES")
_candidates = []
if isinstance(_profiles, (tuple, list)):
    _candidates = [p for p in _profiles
                   if isinstance(p, dict)
                   and p.get("SOURCE_KEY") == "source-two-source"
                   and "CATALOG" in p.get("MODEL_BINDINGS", ())]
if len(_candidates) > 1:
    raise RuntimeError("Multiple Catalog Source Two profiles need review.")

if len(_candidates) == 1:
    source_parts = identifier(_candidates[0]["RAW_TABLE"])
else:
    # A fresh notebook needs no mapper variables or previous hierarchy query.
    # Discover one unambiguous Source/Topic/Section/Sub-Section RAW family in
    # the *current database and schema*, using INFORMATION_SCHEMA only.
    _scope = session.sql(
        "SELECT CURRENT_DATABASE() AS ACTIVE_DB, "
        "CURRENT_SCHEMA() AS ACTIVE_SCHEMA"
    ).collect()
    if len(_scope) != 1:
        raise RuntimeError("Could not resolve the current Snowflake namespace.")
    _scope = _scope[0].as_dict(recursive=True)
    _db, _schema = _scope.get("ACTIVE_DB"), _scope.get("ACTIVE_SCHEMA")
    if not isinstance(_db, str) or not isinstance(_schema, str) or not (
        _SAFE.fullmatch(_db) and _SAFE.fullmatch(_schema)
    ):
        raise RuntimeError(
            "Select the Source Two RAW database/schema in the notebook context."
        )
    _table_rows = session.sql(
        'SELECT TABLE_NAME FROM "' + _db + '".INFORMATION_SCHEMA.TABLES '
        'WHERE TABLE_SCHEMA = ' + literal(_schema.upper())
        + " AND TABLE_NAME LIKE '%RAW'"
    ).collect()
    _available = {
        str(row.as_dict(recursive=True)["TABLE_NAME"]).upper()
        for row in _table_rows
    }
    if not all(_SAFE.fullmatch(name) for name in _available):
        raise RuntimeError("Unexpected source table name in metadata.")
    _families = []
    for _source in sorted(_available):
        if not _source.endswith("_SOURCE_RAW"):
            continue
        _stem = _source[:-len("_SOURCE_RAW")]
        if all(_stem + suffix in _available for suffix in (
            "_TOPIC_RAW", "_SECTION_RAW", "_SUB_SECTION_RAW"
        )):
            _families.append(_source)
    if len(_families) != 1:
        raise RuntimeError(
            "The current database/schema does not identify exactly one four-level "
            "Source Two RAW family. Select that RAW namespace and run this cell again."
        )
    source_parts = (_db, _schema, _families[0])

if not source_parts[2].upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("The Source Two source table needs a _SOURCE_RAW suffix.")
_prefix = source_parts[2][:-len("_SOURCE_RAW")]
level_tables = [
    ("SOURCE", source_parts),
    ("TOPIC", (*source_parts[:2], _prefix + "_TOPIC_RAW")),
    ("SECTION", (*source_parts[:2], _prefix + "_SECTION_RAW")),
    ("SUB_SECTION", (*source_parts[:2], _prefix + "_SUB_SECTION_RAW")),
]
if len({parts for _, parts in level_tables}) != 4:
    raise RuntimeError("The four hierarchy RAW sources must be distinct.")


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
