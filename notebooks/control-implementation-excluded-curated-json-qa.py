# Read-only Source One / SSP Control Implementation excluded-field audit.
# Run in one Python cell of the already-loaded Snowflake SSP mapper notebook.
# No table names, source-field lists, CSV stage, IDs or variables to fill in.
# Uses the exact retained source snapshot and full loaded mapping CSV.

import json

if not all(k in globals() for k in ("MODEL_GRAPHS", "MAPPING_INPUTS", "SOURCE_INPUTS")):
    raise RuntimeError("Use your existing SSP mapper notebook after its source and graph cells.")

ssp = [k for k in MODEL_GRAPHS
       if isinstance(k, tuple) and len(k) == 2 and k[1] == "SSP"]
if len(ssp) != 1:
    raise RuntimeError("Expected exactly one loaded SSP model route.")

source_key = ssp[0][0]
if source_key not in MAPPING_INPUTS or source_key not in SOURCE_INPUTS:
    raise RuntimeError("Current SSP mapping or retained source snapshot unavailable.")

mapping_rows = MAPPING_INPUTS[source_key]
excluded = [r for r in mapping_rows
            if r.get("OSCAL_MODEL") == "SSP - Control Implementation"
            and r.get("EXECUTION_STATUS") == "EXCLUDED"
            and r.get("SOURCE_FIELD_NAME")]
excluded_names = sorted(set(r["SOURCE_FIELD_NAME"] for r in excluded))
if not excluded_names:
    raise RuntimeError("No current Control Implementation exclusion rows found.")

ctx = MODEL_GRAPHS[ssp[0]]["context"]
stats = {name: {
    "rows_present": 0, "populated": 0, "explicit_null": 0,
    "empty_value": 0, "example_content_id": None
} for name in excluded_names}
all_raw_keys = set()
package_count = 0

def contains_business_data(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(contains_business_data(v) for v in value)
    if isinstance(value, dict):
        return any(contains_business_data(v) for v in value.values())
    return True

for record in SOURCE_INPUTS[source_key]["source_df"].to_local_iterator():
    package_count += 1
    content_id = str(record["SOURCE_RECORD_ID"])
    source = _metadata_parse(record, ctx)
    all_raw_keys.update(source)

    for name in excluded_names:
        if name not in source:
            continue
        s = stats[name]
        s["rows_present"] += 1
        value = _to_python(source[name])
        if value is None:
            s["explicit_null"] += 1
        elif contains_business_data(value):
            s["populated"] += 1
            if s["example_content_id"] is None:
                s["example_content_id"] = content_id
        else:
            s["empty_value"] += 1

mapping_names = set(r["SOURCE_FIELD_NAME"] for r in mapping_rows
                    if r.get("SOURCE_FIELD_NAME"))
unmatched = sorted(all_raw_keys - mapping_names)
out = {
    "MAPPING_CSV_ROWS": len(mapping_rows),
    "MAPPING_CSV_DISTINCT_SOURCE_FIELD_NAMES": len(mapping_names),
    "SOURCE_PACKAGES_IN_FROZEN_SNAPSHOT": package_count,
    "CURATED_JSON_DISTINCT_TOP_LEVEL_FIELD_NAMES": len(all_raw_keys),
    "CURATED_JSON_FIELD_NAMES_NOT_LISTED_IN_MAPPING_CSV": len(unmatched),
    "EXCLUDED_CONTROL_IMPLEMENTATION_MAPPING_OCCURRENCES": len(excluded),
    "EXCLUDED_CONTROL_IMPLEMENTATION_DISTINCT_FIELDS": len(excluded_names),
}
print("SOURCE ONE: EXCLUDED CONTROL IMPLEMENTATION FIELD AUDIT")
print(json.dumps(out, indent=2))
print("FIELD RESULTS")
for name in excluded_names:
    s = stats[name]
    status = (
        "NOT_PRESENT_IN_SOURCE_SNAPSHOT" if s["rows_present"] == 0
        else "PRESENT_WITH_POPULATED_DATA" if s["populated"] > 0
        else "PRESENT_ONLY_NULL_OR_EMPTY"
    )
    print(json.dumps({
        "ARCHER_FIELD": name,
        "CSV_MAPPING_OCCURRENCES": sum(
            r["SOURCE_FIELD_NAME"] == name for r in excluded
        ),
        "SOURCE_KEY_PRESENT_PACKAGES": s["rows_present"],
        "POPULATED_PACKAGES": s["populated"],
        "EXPLICIT_NULL_PACKAGES": s["explicit_null"],
        "EMPTY_PACKAGES": s["empty_value"],
        "EXAMPLE_POPULATED_CONTENT_ID": s["example_content_id"],
        "SOURCE_STATUS": status,
        "OSCAL_MAPPING_STATUS": "EXCLUDED"
    }))
print("EXTRA TOP-LEVEL SOURCE KEYS NOT NAMED IN THE CURRENT CSV")
print(json.dumps(unmatched, indent=2))
print("NOTE: Unlisted JSON keys are inventory candidates, not automatically")
print("approved OSCAL mappings. Results use the mapper's retained source snapshot.")
