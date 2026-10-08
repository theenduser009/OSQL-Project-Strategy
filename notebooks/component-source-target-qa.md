# Component Source-to-Target QA

Run this Python cell in the same notebook session after the mapper has been loaded.

Edit only the two values under **QA input**. The check is read-only.

```python
import json

# ------------------------------------------------------------
# QA input
# ------------------------------------------------------------
SOURCE_RECORD_ID = "<SOURCE_RECORD_ID>"
SOURCE_FIELD = "<SOURCE_FIELD_NAME>"
# ------------------------------------------------------------

route = next(
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
)

graph = MODEL_GRAPHS[route]
context = graph["context"]
config = context["config"]
storage = config["STORAGE_CONTRACT"]

component_path = "system-security-plan.system-implementation.components[]"

source_record = next(
    (
        row for row in SOURCE_INPUTS[route[0]]["source_df"].to_local_iterator()
        if row["SOURCE_RECORD_ID"] == SOURCE_RECORD_ID
    ),
    None,
)

if source_record is None:
    raise ValueError("SOURCE_RECORD_ID was not found in the current source snapshot.")

source_object = _metadata_parse(source_record, context)
source_value = resolve_json_path(
    source_object,
    SOURCE_FIELD,
    default=SKIP_VALUE,
)

if source_value is SKIP_VALUE or not _has_value(source_value):
    raise ValueError("The selected source field has no populated value for this record.")

component_ids = _component_reference_content_ids(source_value)

expected = {}

for component_id in component_ids:
    component_uuid = _deterministic_uuid(
        config["IDENTITY_VERSION"],
        config["SOURCE_SYSTEM_NAME"],
        config["SOURCE_TABLE_NAME"],
        SOURCE_RECORD_ID,
        config["OSCAL_MODEL"],
        component_path,
        component_id,
    ).replace("-", "")

    expected[component_uuid] = component_id

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
dim_pk = storage["DIM_PK_COLUMN"]

escaped_record = SOURCE_RECORD_ID.replace("'", "''")
escaped_field = SOURCE_FIELD.replace("'", "''")
uuid_list = ", ".join(
    "'" + value.replace("'", "''") + "'"
    for value in sorted(expected)
)

sql = f"""
SELECT
    c.SOURCE_RECORD_ID,
    c.OSCAL_UUID AS COMPONENT_UUID,
    c.METADATA_JSON:"type"::STRING AS COMPONENT_TYPE,
    c.METADATA_JSON:"title"::STRING AS COMPONENT_TITLE,
    c.METADATA_JSON:"description"::STRING AS COMPONENT_DESCRIPTION,
    p.METADATA_JSON:"value"::STRING AS SOURCE_FIELD
FROM {dim} c
JOIN {fact} f
  ON f.FK_SOURCE_ELEMENT_HASH = c.{dim_pk}
 AND f.DEPENDENCY_TYPE = 'CONTAINS'
JOIN {dim} p
  ON p.{dim_pk} = f.FK_TARGET_ELEMENT_HASH
 AND p.ELEMENT_TYPE = 'props'
 AND p.METADATA_JSON:"name"::STRING = 'source-field'
WHERE c.SOURCE_RECORD_ID = '{escaped_record}'
  AND c.ELEMENT_TYPE = 'components'
  AND c.OSCAL_UUID IN ({uuid_list})
  AND p.METADATA_JSON:"value"::STRING = '{escaped_field}'
ORDER BY c.OSCAL_UUID
"""

persisted = [row.as_dict() for row in session.sql(sql).collect()]

actual_uuids = {
    row["COMPONENT_UUID"]
    for row in persisted
}

expected_uuids = set(expected)

if actual_uuids != expected_uuids:
    raise ValueError(
        "Source-to-target component mismatch: "
        + json.dumps({
            "EXPECTED_COMPONENTS": len(expected_uuids),
            "FOUND_COMPONENTS": len(actual_uuids),
            "MISSING_COMPONENTS": len(expected_uuids - actual_uuids),
            "UNEXPECTED_COMPONENTS": len(actual_uuids - expected_uuids),
        }, indent=2)
    )

result = []

for row in persisted:
    result.append({
        "SOURCE_RECORD_ID": row["SOURCE_RECORD_ID"],
        "SOURCE_FIELD": row["SOURCE_FIELD"],
        "SOURCE_COMPONENT_ID": expected[row["COMPONENT_UUID"]],
        "OSCAL_COMPONENT_UUID": row["COMPONENT_UUID"],
        "COMPONENT_TYPE": row["COMPONENT_TYPE"],
        "COMPONENT_TITLE": row["COMPONENT_TITLE"],
        "COMPONENT_DESCRIPTION": row["COMPONENT_DESCRIPTION"],
    })

print("COMPONENT SOURCE-TO-TARGET QA: PASS")
print(json.dumps({
    "SOURCE_RECORD_ID": SOURCE_RECORD_ID,
    "SOURCE_FIELD": SOURCE_FIELD,
    "SOURCE_COMPONENT_COUNT": len(component_ids),
    "PERSISTED_COMPONENT_COUNT": len(persisted),
    "STATUS": "VERIFIED",
}, indent=2))

print("MATCHED COMPONENTS")
print(json.dumps(result, indent=2, default=str))
```

Expected outcome:

```text
COMPONENT SOURCE-TO-TARGET QA: PASS
SOURCE_COMPONENT_COUNT = PERSISTED_COMPONENT_COUNT
STATUS = VERIFIED
```
