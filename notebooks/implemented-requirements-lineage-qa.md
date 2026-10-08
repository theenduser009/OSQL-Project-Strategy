# Implemented Requirements — Persisted Lineage QA

Run the following **read-only** Python cell in the same Snowflake notebook session after an SSP mapper PREVIEW or COMMIT has populated `MODEL_GRAPHS`. It reads existing persisted DIM/FACT data through the loaded model's storage contract and does not change data.

```python
# Read-only persisted SSP implemented-requirement lineage check.
import json

if not globals().get("MODEL_GRAPHS"):
    raise ValueError("Load the SSP mapper graph/context before this QA.")

routes = [
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
]
if len(routes) != 1:
    raise ValueError("Expected exactly one loaded SSP route.")

ctx = MODEL_GRAPHS[routes[0]]["context"]
storage = ctx["config"]["STORAGE_CONTRACT"]

requirement_path = "system-security-plan.control-implementation.implemented-requirements[]"
member_sources = {"control-id": set(), "remarks": set()}

for mapping in ctx["mapping_rows"]:
    if mapping.get("OWNER_ELEMENT_PATH") != requirement_path:
        continue
    if not mapping.get("LINEAGE_REQUIRED_FLAG"):
        continue
    member = (mapping.get("REPRESENTATION_PARAMS") or {}).get("target")
    if member in member_sources:
        member_sources[member].add(mapping["SOURCE_FIELD_NAME"])

if any(len(fields) != 1 for fields in member_sources.values()):
    raise ValueError("Requirement member-to-source-field lineage is missing or ambiguous.")

def sql_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
key = storage["DIM_PK_COLUMN"]
source_field_control = sql_quote(next(iter(member_sources["control-id"])))
source_field_remarks = sql_quote(next(iter(member_sources["remarks"])))
source_system = sql_quote(storage["SOURCE_SYSTEM_NAME"])
source_table = sql_quote(storage["SOURCE_TABLE_NAME"])

query = f"""
WITH requirement_props AS (
  SELECT
    r.{key} AS REQUIREMENT_KEY,
    r.METADATA_JSON:"control-id"::STRING AS CONTROL_ID,
    r.METADATA_JSON:"remarks"::STRING AS REMARKS,
    COALESCE(COUNT_IF(
      p.METADATA_JSON:"name"::STRING = 'source-field'
      AND p.METADATA_JSON:"value"::STRING = {source_field_control}
    ), 0) AS CONTROL_LINEAGE_COUNT,
    COALESCE(COUNT_IF(
      p.METADATA_JSON:"name"::STRING = 'source-field'
      AND p.METADATA_JSON:"value"::STRING = {source_field_remarks}
    ), 0) AS REMARKS_LINEAGE_COUNT
  FROM {dim} r
  LEFT JOIN {fact} f
    ON f.FK_SOURCE_ELEMENT_HASH = r.{key}
   AND f.DEPENDENCY_TYPE = 'CONTAINS'
  LEFT JOIN {dim} p
    ON p.{key} = f.FK_TARGET_ELEMENT_HASH
   AND p.ELEMENT_TYPE = 'props'
  WHERE r.ELEMENT_TYPE = 'implemented-requirements'
    AND r.SOURCE_SYSTEM_NAME = {source_system}
    AND r.SOURCE_TABLE_NAME = {source_table}
  GROUP BY
    r.{key},
    r.METADATA_JSON:"control-id"::STRING,
    r.METADATA_JSON:"remarks"::STRING
)
SELECT
  COUNT(*) AS REQUIREMENT_ROWS,
  COALESCE(COUNT_IF(CONTROL_ID IS NOT NULL AND CONTROL_ID <> ''), 0)
    AS POPULATED_CONTROL_IDS,
  COALESCE(COUNT_IF(CONTROL_ID IS NULL OR CONTROL_ID = ''), 0)
    AS MISSING_CONTROL_IDS,
  COALESCE(COUNT_IF(CONTROL_ID IS NOT NULL AND CONTROL_ID <> ''
     AND CONTROL_LINEAGE_COUNT <> 1), 0)
    AS CONTROL_ID_LINEAGE_ERRORS,
  COALESCE(COUNT_IF(REMARKS IS NOT NULL AND REMARKS <> ''), 0)
    AS POPULATED_REMARKS,
  COALESCE(COUNT_IF(REMARKS IS NOT NULL AND REMARKS <> ''
     AND REMARKS_LINEAGE_COUNT <> 1), 0)
    AS REMARKS_LINEAGE_ERRORS
FROM requirement_props
"""

row = session.sql(query).collect()[0]
summary = {name: int(row[name] or 0) for name in (
    "REQUIREMENT_ROWS",
    "POPULATED_CONTROL_IDS",
    "MISSING_CONTROL_IDS",
    "CONTROL_ID_LINEAGE_ERRORS",
    "POPULATED_REMARKS",
    "REMARKS_LINEAGE_ERRORS",
)}

if summary["REQUIREMENT_ROWS"] == 0:
    status = "NO_REQUIREMENTS_TO_TEST"
elif summary["MISSING_CONTROL_IDS"] or summary["CONTROL_ID_LINEAGE_ERRORS"] or summary["REMARKS_LINEAGE_ERRORS"]:
    status = "REVIEW_REQUIRED"
elif summary["POPULATED_REMARKS"] == 0:
    status = "NO_POPULATED_REMARKS_TO_TEST"
else:
    status = "VERIFIED"

print("IMPLEMENTED REQUIREMENT PERSISTED LINEAGE QA")
print(json.dumps({**summary, "STATUS": status}, indent=2))
```

A result of `STATUS = VERIFIED` means populated persisted control identifiers and remarks each have exactly one expected local source-field lineage property for the current source namespace. It is **not** yet an Archer-versus-OSCAL source-value equality test; compare original source values separately. A count of zero does not establish a passing mapping. No DML, DDL, or mapper COMMIT is needed for this QA.
