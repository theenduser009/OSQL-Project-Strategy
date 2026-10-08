# Component Lineage PREVIEW Check

Run this Python cell in the same notebook session after the SSP PREVIEW completes.

```python
import json

route = next(
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
)

graph = MODEL_GRAPHS[route]

components = {}
lineage = {}

for row in graph["nodes"].to_local_iterator():
    path = row["ELEMENT_PATH"]

    if path.endswith(".system-implementation.components[]"):
        key = (row["SOURCE_RECORD_ID"], row["INSTANCE_KEY"])
        components[key] = row

    elif path.endswith(".system-implementation.components[].props[]"):
        payload = (
            json.loads(row["METADATA_JSON"])
            if isinstance(row["METADATA_JSON"], str)
            else row["METADATA_JSON"]
        )

        if payload.get("name") == "source-field":
            key = (
                row["SOURCE_RECORD_ID"],
                row["PARENT_INSTANCE_KEY"],
            )
            lineage.setdefault(key, []).append(
                payload.get("value")
            )

missing = [
    key for key in components
    if not lineage.get(key)
]

if missing:
    raise ValueError(
        "Component lineage missing for "
        + str(len(missing))
        + " component rows."
    )

field_counts = {}

for fields in lineage.values():
    for field in fields:
        field_counts[field] = (
            field_counts.get(field, 0) + 1
        )

print("COMPONENT LINEAGE PREVIEW: PASS")

print(json.dumps({
    "COMPONENT_ROWS": len(components),
    "COMPONENTS_WITH_LINEAGE": len(lineage),
    "MISSING_COMPONENT_LINEAGE": len(missing),
    "FIELD_COUNTS": field_counts,
    "STATUS": "VERIFIED",
}, indent=2))
```

Expected outcome:

```text
COMPONENT LINEAGE PREVIEW: PASS
MISSING_COMPONENT_LINEAGE = 0
STATUS = VERIFIED
```
