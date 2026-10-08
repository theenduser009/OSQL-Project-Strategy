# Implemented Requirements — Source-to-Target Value QA

Run this **read-only** Python cell after the SSP mapper context is loaded in the same Snowflake notebook session. It samples actual child-source records from the configured joined lookup, uses the mapper's existing transformations and deterministic requirement UUID, and compares the resulting values to persisted OSCAL `control-id` and `remarks`. No target writes, table changes, or reloads.

```python
import json
from snowflake.snowpark import functions as F

MAX_SAMPLES = 15
MAX_CANDIDATES = 1000
requirement_path = "system-security-plan.control-implementation.implemented-requirements[]"
target_members = ("control-id", "remarks")

# Use only the currently loaded SSP source/model route and compiled mapping.
routes = [
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
]
if len(routes) != 1:
    raise ValueError("Exactly one loaded SSP mapper route is required.")
route = routes[0]
ctx = MODEL_GRAPHS[route]["context"]
cfg = ctx["config"]
storage = cfg["STORAGE_CONTRACT"]

mapping = {}
for row in ctx["mapping_rows"]:
    if row.get("OWNER_ELEMENT_PATH") != requirement_path:
        continue
    member = (row.get("REPRESENTATION_PARAMS") or {}).get("target")
    if member in target_members:
        if member in mapping or row.get("REPRESENTATION") != "joined-records":
            raise ValueError("Expected one unambiguous joined mapping per requirement member.")
        mapping[member] = row
if set(mapping) != set(target_members):
    raise ValueError("Required native member mapping is missing.")

bindings = {
    (row.get("REPRESENTATION_PARAMS") or {}).get("joined_lookup")
    for row in mapping.values()
}
if len(bindings) != 1 or None in bindings:
    raise ValueError("Requirement mappings must share one joined source.")
binding = next(iter(bindings))
source = ctx["lookups"]["joined_sources"][binding]
identity_field = ctx["compiled_plan"]["elements"][requirement_path]["parameters"]["joined_instance_field"]

# Candidate rows must have both named source fields; the loop below also checks
# actual approved transformation output (including empty/null behavior).
raw = F.col("CURATED_JSON")
control_source = mapping["control-id"]["SOURCE_FIELD_NAME"]
remarks_source = mapping["remarks"]["SOURCE_FIELD_NAME"]
candidates = (
    source
    .filter(
        F.get(raw, F.lit(identity_field)).is_not_null()
        & F.get(raw, F.lit(control_source)).is_not_null()
        & F.get(raw, F.lit(remarks_source)).is_not_null()
    )
    .sort("CONTENT_ID", "_SOURCE_RECORD_ID")
    .limit(MAX_CANDIDATES)
    .collect()
)

qa_ctx = dict(ctx)
qa_ctx["graph_report"] = {"STATUS": "NOT_RUN", "MAPPED_VALUES": 0, "MISSING_VALUES": 0}
expected = {}
for item in candidates:
    child = _metadata_parse(item, ctx)
    identity = resolve_json_path(child, identity_field, default=SKIP_VALUE)
    if identity is SKIP_VALUE or not _has_value(identity):
        continue
    identity = _scalar_text(identity, "Invalid joined identity", "Empty joined identity")

    control = _metadata_mapped_value(mapping["control-id"], child, qa_ctx)
    remarks = _metadata_mapped_value(mapping["remarks"], child, qa_ctx)
    if control is SKIP_VALUE or remarks is SKIP_VALUE:
        continue
    if control is None or remarks is None:
        continue

    parent_id = str(item["CONTENT_ID"]).strip()
    node_uuid = _deterministic_uuid(
        cfg["IDENTITY_VERSION"],
        cfg["SOURCE_SYSTEM_NAME"],
        cfg["SOURCE_TABLE_NAME"],
        parent_id,
        cfg["OSCAL_MODEL"],
        requirement_path,
        identity,
    ).replace("-", "")

    candidate = {
        "parent": parent_id,
        "child": str(item["_SOURCE_RECORD_ID"]),
        "control-id": control,
        "remarks": remarks,
    }
    if node_uuid in expected and expected[node_uuid] != candidate:
        raise ValueError("One requirement identity has conflicting source values.")
    expected[node_uuid] = candidate
    if len(expected) >= MAX_SAMPLES:
        break

if not expected:
    raise ValueError("No populated source requirements available for a value comparison.")

# Persisted DIM is read-only; exact member strings are compared in Python.
persisted_rows = (
    session.table(storage["TARGET_DIM"])
    .filter(F.col("OSCAL_UUID").isin(*sorted(expected)))
    .select(
        "OSCAL_UUID", "SOURCE_RECORD_ID", "SOURCE_SYSTEM_NAME",
        "SOURCE_TABLE_NAME", "ELEMENT_TYPE", "METADATA_JSON",
    )
    .collect()
)

actual = {}
for item in persisted_rows:
    uuid = item["OSCAL_UUID"]
    if uuid in actual:
        raise ValueError("Duplicate persisted requirement UUID.")
    actual[uuid] = item

failures = []
control_equal = 0
remarks_equal = 0
for uuid, source_values in expected.items():
    saved = actual.get(uuid)
    if saved is None:
        failures.append({"SOURCE_CHILD_ID": source_values["child"], "ISSUE": "MISSING_TARGET"})
        continue

    payload = saved["METADATA_JSON"]
    payload = json.loads(payload) if isinstance(payload, str) else _to_python(payload)
    provenance_ok = (
        saved["SOURCE_RECORD_ID"] == source_values["parent"]
        and saved["SOURCE_SYSTEM_NAME"] == cfg["SOURCE_SYSTEM_NAME"]
        and saved["SOURCE_TABLE_NAME"] == cfg["SOURCE_TABLE_NAME"]
        and saved["ELEMENT_TYPE"] == "implemented-requirements"
    )
    control_ok = isinstance(payload, dict) and payload.get("control-id") == source_values["control-id"]
    remarks_ok = isinstance(payload, dict) and payload.get("remarks") == source_values["remarks"]
    control_equal += int(control_ok and provenance_ok)
    remarks_equal += int(remarks_ok and provenance_ok)

    if not (provenance_ok and control_ok and remarks_ok):
        failures.append({
            "SOURCE_CHILD_ID": source_values["child"],
            "PROVENANCE_MATCH": provenance_ok,
            "CONTROL_ID_MATCH": control_ok,
            "REMARKS_MATCH": remarks_ok,
        })

print("IMPLEMENTED REQUIREMENTS SOURCE-TO-TARGET SAMPLE QA")
print(json.dumps({
    "SAMPLED_REQUIREMENTS": len(expected),
    "CONTROL_ID_VALUE_MATCHES": control_equal,
    "REMARKS_VALUE_MATCHES": remarks_equal,
    "MISMATCHES": len(failures),
    "STATUS": "SAMPLE_VERIFIED" if not failures else "REVIEW_REQUIRED",
}, indent=2))
if failures:
    print("FIRST_FAILURES (IDs/status only; no source values)")
    print(json.dumps(failures[:10], indent=2))
```

**Pass criterion:** the sample reports `SAMPLE_VERIFIED`, with zero mismatches and both matched-value counts equal to `SAMPLED_REQUIREMENTS`.

This checks a deterministic, bounded sample of source records where both fields are populated. It does **not** prove full-source coverage, null/omission cases, same-snapshot row-count parity, or complete OSCAL schema conformance. It must not be treated as a mapper PREVIEW/COMMIT.
