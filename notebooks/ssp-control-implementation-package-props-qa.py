# SSP Control Implementation: read-only package property value reconciliation.
# Run in the existing SSP Snowflake notebook session with MODEL_GRAPHS and SOURCE_INPUTS.
# Compares all approved Control Implementation package-level props at the exact
# system-characteristics parent via persisted FACT CONTAINS edges.
# No DML, DDL, or COMMIT. No actual source values are printed.
import json
from collections import defaultdict

OWNER_PATH = "system-security-plan.system-characteristics.props[]"
MAPPING_GROUP = "SSP - Control Implementation"
MAX_ISSUES_SHOWN = 10

if not globals().get("MODEL_GRAPHS") or not globals().get("SOURCE_INPUTS"):
    raise ValueError("Load the SSP mapper graph and source snapshot before this QA")
routes = [
    k for k in MODEL_GRAPHS
    if isinstance(k, tuple) and len(k) == 2 and k[1] == "SSP"
]
if len(routes) != 1:
    raise ValueError("Exactly one selected SSP route is required")
route = routes[0]
ctx = MODEL_GRAPHS[route]["context"]
config = ctx["config"]
storage = config["STORAGE_CONTRACT"]

prop_rows = [
    row for row in ctx["mapping_rows"]
    if row.get("ARTIFACT_MODEL") == MAPPING_GROUP
    and row.get("OWNER_ELEMENT_PATH") == OWNER_PATH
    and row.get("REPRESENTATION") == "properties"
    and row.get("TRANSFORM_ID") != "skip"
]
if not prop_rows:
    raise ValueError("No approved package property rows are loaded")

def prop_name(row):
    return (_metadata_params(row).get("property_name")
            or _stable_property_name(row["SOURCE_FIELD_NAME"]))

names = [prop_name(row) for row in prop_rows]
if len(names) != len(set(names)):
    raise ValueError("Ambiguous approved property names")
other_names = [
    prop_name(row) for row in ctx["mapping_rows"]
    if row.get("OWNER_ELEMENT_PATH") == OWNER_PATH
    and row.get("REPRESENTATION") == "properties"
    and row.get("ARTIFACT_MODEL") != MAPPING_GROUP
]
if set(other_names) & set(names):
    raise ValueError("Property name collides with a different SSP section")

by_name = {prop_name(row): row for row in prop_rows}
qa_ctx = dict(ctx)
qa_ctx["graph_report"] = {
    "STATUS": "NOT_RUN", "MAPPED_VALUES": 0, "MISSING_VALUES": 0
}

source_counts = {
    name: {"present": 0, "populated": 0, "explicit_null": 0}
    for name in names
}
expected = defaultdict(list)
source_ids = set()
transform_issues = []

for source_record in SOURCE_INPUTS[route[0]]["source_df"].to_local_iterator():
    rid = str(source_record["SOURCE_RECORD_ID"])
    if rid in source_ids:
        raise ValueError("Duplicate frozen source record identity")
    source_ids.add(rid)
    source_obj = _metadata_parse(source_record, ctx)

    for name, mapping in by_name.items():
        field = mapping["SOURCE_FIELD_NAME"]
        raw = resolve_json_path(source_obj, field, default=SKIP_VALUE)
        if raw is not SKIP_VALUE:
            source_counts[name]["present"] += 1
        if raw is None:
            source_counts[name]["explicit_null"] += 1
        if raw is not SKIP_VALUE and _has_value(raw):
            source_counts[name]["populated"] += 1

        try:
            value = _metadata_mapped_value(mapping, source_obj, qa_ctx)
            if value is SKIP_VALUE:
                continue
            values = [None] if value is None else _oscal_property_values(value)
            expected[(rid, name)].extend(values)
        except (TypeError, ValueError, ArithmeticError) as exc:
            transform_issues.append({
                "SOURCE_RECORD_ID": rid,
                "SOURCE_FIELD_NAME": field,
                "ISSUE": "TRANSFORM_" + type(exc).__name__
            })

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
pk = storage["DIM_PK_COLUMN"]
quoted_names = ", ".join(quote(name) for name in sorted(names))
source_system = quote(config["SOURCE_SYSTEM_NAME"])
source_table = quote(config["SOURCE_TABLE_NAME"])

query = f"""
SELECT child.SOURCE_RECORD_ID AS SOURCE_RECORD_ID,
       TO_JSON(child.METADATA_JSON) AS PROPERTY_JSON
FROM {dim} parent
JOIN {fact} edge
  ON edge.FK_SOURCE_ELEMENT_HASH = parent.{pk}
 AND edge.DEPENDENCY_TYPE = 'CONTAINS'
JOIN {dim} child
  ON child.{pk} = edge.FK_TARGET_ELEMENT_HASH
WHERE parent.ELEMENT_TYPE = 'system-characteristics'
  AND child.ELEMENT_TYPE = 'props'
  AND parent.SOURCE_SYSTEM_NAME = {source_system}
  AND parent.SOURCE_TABLE_NAME = {source_table}
  AND child.SOURCE_SYSTEM_NAME = {source_system}
  AND child.SOURCE_TABLE_NAME = {source_table}
  AND parent.SOURCE_RECORD_ID = child.SOURCE_RECORD_ID
  AND child.METADATA_JSON:"name"::STRING IN ({quoted_names})
"""

actual = defaultdict(list)
invalid_target = []
for saved in session.sql(query).to_local_iterator():
    rid = str(saved["SOURCE_RECORD_ID"])
    text_payload = saved["PROPERTY_JSON"]
    payload = json.loads(text_payload) if text_payload is not None else None
    if not isinstance(payload, dict) or "name" not in payload or "value" not in payload:
        invalid_target.append({
            "SOURCE_RECORD_ID": rid, "ISSUE": "INVALID_PROP_PAYLOAD"
        })
        continue
    if rid not in source_ids:
        invalid_target.append({
            "SOURCE_RECORD_ID": rid, "ISSUE": "TARGET_RECORD_OUTSIDE_SOURCE"
        })
    actual[(rid, payload["name"])].append(payload["value"])

def canonical(values):
    return sorted(
        json.dumps(v, sort_keys=True, default=str, allow_nan=False)
        for v in values
    )

rows = []
issues = list(transform_issues) + list(invalid_target)
all_keys = set(expected) | set(actual)
for name, mapping in sorted(by_name.items()):
    ids = sorted({rid for (rid, prop) in all_keys if prop == name})
    matched = 0
    mismatched = 0
    expected_rows = 0
    persisted_rows = 0

    for rid in ids:
        left = expected.get((rid, name), [])
        right = actual.get((rid, name), [])
        expected_rows += len(left)
        persisted_rows += len(right)
        if canonical(left) == canonical(right):
            matched += 1
        else:
            mismatched += 1
            issues.append({
                "SOURCE_RECORD_ID": rid,
                "SOURCE_FIELD_NAME": mapping["SOURCE_FIELD_NAME"],
                "ISSUE": "EXACT_PROP_VALUE_OR_PLACEMENT_MISMATCH",
                "EXPECTED_OCCURRENCES": len(left),
                "PERSISTED_OCCURRENCES": len(right)
            })

    counts = source_counts[name]
    errors = sum(
        item["SOURCE_FIELD_NAME"] == mapping["SOURCE_FIELD_NAME"]
        for item in transform_issues
    )
    if mismatched or errors:
        status = "REVIEW_REQUIRED"
    elif counts["populated"] > 0:
        status = "POPULATED_VALUE_PARITY_VERIFIED"
    elif counts["explicit_null"] > 0:
        status = "NULL_ONLY_PARITY_VERIFIED"
    else:
        status = "NO_POPULATED_SOURCE_DATA"

    rows.append({
        "SOURCE_FIELD_NAME": mapping["SOURCE_FIELD_NAME"],
        "OSCAL_PROPERTY_NAME": name,
        "SOURCE_PRESENT": counts["present"],
        "SOURCE_POPULATED": counts["populated"],
        "SOURCE_EXPLICIT_NULL": counts["explicit_null"],
        "EXPECTED_PROP_ROWS": expected_rows,
        "PERSISTED_PROP_ROWS": persisted_rows,
        "EXACT_MATCHING_RECORDS": matched,
        "MISMATCH_RECORDS": mismatched,
        "STATUS": status
    })

report = {
    "MAPPED_PACKAGE_PROP_FIELDS": len(rows),
    "SOURCE_PACKAGES": len(source_ids),
    "POPULATED_FIELDS_VERIFIED": sum(
        row["STATUS"] == "POPULATED_VALUE_PARITY_VERIFIED" for row in rows
    ),
    "NULL_ONLY_FIELDS_VERIFIED": sum(
        row["STATUS"] == "NULL_ONLY_PARITY_VERIFIED" for row in rows
    ),
    "NO_POPULATED_SOURCE_FIELDS": sum(
        row["STATUS"] == "NO_POPULATED_SOURCE_DATA" for row in rows
    ),
    "PROP_MISMATCH_RECORDS": sum(row["MISMATCH_RECORDS"] for row in rows),
    "SOURCE_TRANSFORM_ERRORS": len(transform_issues),
    "INVALID_OR_EXTRA_TARGET_ROWS": len(invalid_target),
    "STATUS": "VERIFIED" if not issues else "REVIEW_REQUIRED"
}
print("CONTROL IMPLEMENTATION PACKAGE PROPS QA")
print(json.dumps(report, indent=2))
print("FIELD RESULTS")
for row in rows:
    print(json.dumps(row))
if issues:
    print("FIRST ISSUES (IDs/counts only, no source values)")
    print(json.dumps(issues[:MAX_ISSUES_SHOWN], indent=2))
