# Persisted Component Lineage Check

Run this Python cell in the same notebook session after the SSP COMMIT completes.

The check is read-only. It obtains the target DIM/FACT names from the mapper's existing
storage contract, compares persisted component lineage with the committed candidate graph,
and prints counts only.

```python
import json

route = next(
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
)

graph = MODEL_GRAPHS[route]
context = graph["context"]
storage = context["config"]["STORAGE_CONTRACT"]

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
dim_pk = storage["DIM_PK_COLUMN"]

source_system = storage["SOURCE_SYSTEM_NAME"].replace("'", "''")
source_table = storage["SOURCE_TABLE_NAME"].replace("'", "''")

component_path = "system-security-plan.system-implementation.components[]"
props_path = component_path + ".props[]"

candidate_components = set()
candidate_field_counts = {}

for row in graph["nodes"].to_local_iterator():
    path = row["ELEMENT_PATH"]

    if path == component_path:
        candidate_components.add(
            (row["SOURCE_RECORD_ID"], row["INSTANCE_KEY"])
        )

    elif path == props_path:
        payload = (
            json.loads(row["METADATA_JSON"])
            if isinstance(row["METADATA_JSON"], str)
            else row["METADATA_JSON"]
        )

        if payload.get("name") == "source-field":
            field = payload.get("value")
            candidate_field_counts[field] = (
                candidate_field_counts.get(field, 0) + 1
            )

candidate_lineage_rows = sum(candidate_field_counts.values())

summary_sql = f"""
WITH per_component AS (
    SELECT
        c.{dim_pk} AS component_key,
        COUNT_IF(
            p.ELEMENT_TYPE = 'props'
            AND p.METADATA_JSON:"name"::STRING = 'source-field'
        ) AS lineage_rows
    FROM {dim} c
    LEFT JOIN {fact} f
      ON f.FK_SOURCE_ELEMENT_HASH = c.{dim_pk}
     AND f.DEPENDENCY_TYPE = 'CONTAINS'
    LEFT JOIN {dim} p
      ON p.{dim_pk} = f.FK_TARGET_ELEMENT_HASH
    WHERE c.ELEMENT_TYPE = 'components'
      AND c.SOURCE_SYSTEM_NAME = '{source_system}'
      AND c.SOURCE_TABLE_NAME = '{source_table}'
    GROUP BY c.{dim_pk}
)
SELECT
    COUNT(*) AS COMPONENT_ROWS,
    COUNT_IF(lineage_rows > 0) AS COMPONENTS_WITH_LINEAGE,
    COALESCE(SUM(lineage_rows), 0) AS LINEAGE_ROWS,
    COUNT_IF(lineage_rows = 0) AS MISSING_COMPONENT_LINEAGE
FROM per_component
"""

field_sql = f"""
SELECT
    p.METADATA_JSON:"value"::STRING AS SOURCE_FIELD,
    COUNT(*) AS ROW_COUNT
FROM {dim} c
JOIN {fact} f
  ON f.FK_SOURCE_ELEMENT_HASH = c.{dim_pk}
 AND f.DEPENDENCY_TYPE = 'CONTAINS'
JOIN {dim} p
  ON p.{dim_pk} = f.FK_TARGET_ELEMENT_HASH
 AND p.ELEMENT_TYPE = 'props'
 AND p.METADATA_JSON:"name"::STRING = 'source-field'
WHERE c.ELEMENT_TYPE = 'components'
  AND c.SOURCE_SYSTEM_NAME = '{source_system}'
  AND c.SOURCE_TABLE_NAME = '{source_table}'
GROUP BY 1
ORDER BY 1
"""

summary = session.sql(summary_sql).collect()[0].as_dict()

persisted_field_counts = {
    row["SOURCE_FIELD"]: int(row["ROW_COUNT"])
    for row in session.sql(field_sql).collect()
}

expected = {
    "COMPONENT_ROWS": len(candidate_components),
    "COMPONENTS_WITH_LINEAGE": len(candidate_components),
    "LINEAGE_ROWS": candidate_lineage_rows,
    "MISSING_COMPONENT_LINEAGE": 0,
}

actual = {
    key: int(summary[key])
    for key in expected
}

if actual != expected:
    raise ValueError(
        "Persisted component lineage count mismatch: "
        + json.dumps({
            "expected": expected,
            "actual": actual,
        }, indent=2)
    )

if persisted_field_counts != candidate_field_counts:
    raise ValueError(
        "Persisted component lineage field-count mismatch: "
        + json.dumps({
            "expected_field_counts": candidate_field_counts,
            "actual_field_counts": persisted_field_counts,
        }, indent=2)
    )

print("PERSISTED COMPONENT LINEAGE: PASS")
print(json.dumps({
    **actual,
    "FIELD_COUNTS": persisted_field_counts,
    "STATUS": "VERIFIED",
}, indent=2))
```

Expected outcome:

```text
PERSISTED COMPONENT LINEAGE: PASS
MISSING_COMPONENT_LINEAGE = 0
STATUS = VERIFIED
```
