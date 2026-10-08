# Find Records with a Populated Component Field

Run this Python cell in the same notebook session after the mapper inputs have been loaded.

Edit only `SOURCE_FIELD`.

```python
SOURCE_FIELD = "<SOURCE_FIELD_NAME>"
MAX_RESULTS = 20

route = next(
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
)

context = MODEL_GRAPHS[route]["context"]
source_df = SOURCE_INPUTS[route[0]]["source_df"]

matches = []

for record in source_df.to_local_iterator():
    source_object = _metadata_parse(record, context)
    value = resolve_json_path(
        source_object,
        SOURCE_FIELD,
        default=SKIP_VALUE,
    )

    if value is SKIP_VALUE or not _has_value(value):
        continue

    component_ids = _component_reference_content_ids(value)

    matches.append({
        "SOURCE_RECORD_ID": record["SOURCE_RECORD_ID"],
        "COMPONENT_COUNT": len(component_ids),
    })

    if len(matches) >= MAX_RESULTS:
        break

print("POPULATED COMPONENT FIELD RECORDS")
print("SOURCE_FIELD =", SOURCE_FIELD)
print("MATCHES_SHOWN =", len(matches))

for row in matches:
    print(
        row["SOURCE_RECORD_ID"],
        "component_count=",
        row["COMPONENT_COUNT"],
    )
```

Use one returned `SOURCE_RECORD_ID` with the separate component source-to-target QA example.
