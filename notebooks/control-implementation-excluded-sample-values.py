# Source One SSP: inspect excluded source fields before changing mapping status.
# One READ-ONLY cell in an existing loaded Snowflake mapper Python notebook.
# Field names, source snapshot and configuration are loaded from its context.
# No source field names, table names, file stages, IDs or parameters to enter.
# Sample VALUES appear only in your notebook output, never in this GitHub file.

import json

if not all(k in globals() for k in ("MODEL_GRAPHS", "MAPPING_INPUTS", "SOURCE_INPUTS")):
    raise RuntimeError("Run after the source/mapping cells in your current SSP notebook.")

routes = [route for route in MODEL_GRAPHS
          if isinstance(route, tuple) and len(route) == 2 and route[1] == "SSP"]
if len(routes) != 1:
    raise RuntimeError("Expected exactly one SSP route in the loaded notebook.")
source_key = routes[0][0]
if source_key not in MAPPING_INPUTS or source_key not in SOURCE_INPUTS:
    raise RuntimeError("Current CSV mapping or retained source snapshot not loaded.")

excluded_rows = [
    row for row in MAPPING_INPUTS[source_key]
    if row.get("OSCAL_MODEL") == "SSP - Control Implementation"
    and row.get("EXECUTION_STATUS") == "EXCLUDED"
    and row.get("SOURCE_FIELD_NAME")
]
fields = sorted(set(row["SOURCE_FIELD_NAME"] for row in excluded_rows))
if not fields:
    raise RuntimeError("No Control Implementation exclusions in the current CSV.")

def contains_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(contains_value(x) for x in value)
    if isinstance(value, dict):
        return any(contains_value(x) for x in value.values())
    # Boolean False and numeric zero are present values. Inspect examples.
    return True

counts = {field: {"key_present": 0, "populated": 0,
                  "null": 0, "empty": 0, "samples": []}
          for field in fields}

ctx = MODEL_GRAPHS[routes[0]]["context"]
package_count = 0
for record in SOURCE_INPUTS[source_key]["source_df"].to_local_iterator():
    package_count += 1
    source = _metadata_parse(record, ctx)
    content_id = str(record["SOURCE_RECORD_ID"])
    for field in fields:
        if field not in source:
            continue
        s = counts[field]
        s["key_present"] += 1
        value = _to_python(source[field])
        if value is None:
            s["null"] += 1
        elif not contains_value(value):
            s["empty"] += 1
        else:
            s["populated"] += 1
            example = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                 default=str)
            if all(v["preview"] != example[:300] for v in s["samples"]):
                if len(s["samples"]) < 3:
                    s["samples"].append({
                        "content_id": content_id,
                        "value_type": type(value).__name__,
                        "preview": example[:300]
                    })

print("SSP CONTROL IMPLEMENTATION: EXCLUDED FIELDS — SOURCE VALUE REVIEW")
print("Packages scanned:", package_count)
print("Excluded CSV rows:", len(excluded_rows), "| distinct fields:", len(fields))
for field in fields:
    s = counts[field]
    classification = (
        "ABSENT" if s["key_present"] == 0
        else "PRESENT_WITH_VALUES" if s["populated"] > 0
        else "PRESENT_NULL_ONLY" if s["null"] == s["key_present"]
        else "PRESENT_NULL_OR_EMPTY"
    )
    print(json.dumps({
        "field": field,
        "status_in_csv": "EXCLUDED",
        "source_status": classification,
        "present_packages": s["key_present"],
        "populated_packages": s["populated"],
        "explicit_null_packages": s["null"],
        "empty_packages": s["empty"],
        "sample_values": s["samples"]
    }, ensure_ascii=False, default=str))

print("Review the five source-populated fields for business meaning.")
print("False/0/nonempty JSON structures count as present; this audit")
print("does not determine whether a field belongs in OSCAL.")
print("No mapper execution, DML, or target changes were performed.")
