# Implemented Requirements — Source-to-Target Value QA

Read-only validation for populated SSP `implemented-requirements[]` source values against persisted OSCAL values. Run in the **same Snowflake notebook session** after the SSP mapper has created `MODEL_GRAPHS`. This check uses the mapper's retained joined-record projection and the actual candidate graph UUID; it does **not** reconstruct component identity from a separately parsed RAW JSON object.

**October 8 correction:** The earlier source-value QA generated a UUID from the raw child JSON and reported all 15 samples as `MISSING_TARGET`. The current joined-record mapper explicitly retains a projected source identity representation. Those identities must not be silently re-normalized in the QA helper. The previous 15/15 output is **inconclusive**, not evidence that the 15 requirements are absent. This version separately checks source-to-candidate identity, candidate payload equality, and persisted-value equality.

```python
import json
from snowflake.snowpark import functions as F

MAX_SAMPLES = 15  # One populated child requirement per source package.
requirement_path = "system-security-plan.control-implementation.implemented-requirements[]"
required_members = {"control-id", "remarks"}

routes = [
    route for route in MODEL_GRAPHS
    if isinstance(route, tuple) and len(route) == 2 and route[1] == "SSP"
]
if len(routes) != 1:
    raise ValueError("Load exactly one SSP route before this QA.")
graph = MODEL_GRAPHS[routes[0]]
ctx = graph["context"]
cfg = ctx["config"]
storage = cfg["STORAGE_CONTRACT"]

mappings = {}
for row in ctx["mapping_rows"]:
    if row.get("OWNER_ELEMENT_PATH") != requirement_path:
        continue
    member = (row.get("REPRESENTATION_PARAMS") or {}).get("target")
    if member in required_members:
        if member in mappings or row.get("REPRESENTATION") != "joined-records":
            raise ValueError("Ambiguous or non-joined requirement member mapping.")
        mappings[member] = row
if set(mappings) != required_members:
    raise ValueError("Required native requirement mappings are missing.")

bindings = {
    (row.get("REPRESENTATION_PARAMS") or {}).get("joined_lookup")
    for row in mappings.values()
}
if len(bindings) != 1 or None in bindings:
    raise ValueError("Requirement members must share one joined source binding.")
binding = next(iter(bindings))
joined = ctx.get("joined_record_lookups", {}).get(binding)
if not isinstance(joined, dict) or not joined:
    raise ValueError("Mapper joined-record snapshot is missing; do not reconstruct it from RAW.")

identity_field = ctx["compiled_plan"]["elements"][requirement_path][
    "parameters"
]["joined_instance_field"]

# Read only retained child payloads actually used by the mapper. The identity
# field was intentionally preserved without the mapped-value JSON decoding.
qa_ctx = dict(ctx)
qa_ctx["graph_report"] = {"STATUS": "NOT_RUN", "MAPPED_VALUES": 0, "MISSING_VALUES": 0}
expected = {}
for parent_id in sorted(joined):
    children = sorted(
        joined[parent_id],
        key=lambda item: str(item.get("source_record_id") or ""),
    )
    for child_record in children:
        source = child_record["payload"]
        identity_raw = resolve_json_path(source, identity_field, default=SKIP_VALUE)
        if identity_raw is SKIP_VALUE or not _has_value(identity_raw):
            continue
        instance_key = _scalar_text(
            identity_raw, "Invalid joined identity", "Blank joined identity"
        )
        control_id = _metadata_mapped_value(mappings["control-id"], source, qa_ctx)
        remarks = _metadata_mapped_value(mappings["remarks"], source, qa_ctx)
        if any(
            value is SKIP_VALUE or not _has_value(value)
            for value in (control_id, remarks)
        ):
            continue
        expected[(str(parent_id), instance_key)] = {
            "child_id": str(child_record["source_record_id"]),
            "control-id": control_id,
            "remarks": remarks,
        }
        break  # One comparable child from this package.
    if len(expected) >= MAX_SAMPLES:
        break

if not expected:
    raise ValueError("No source packages have comparable populated requirement members.")

parents = sorted({parent_id for parent_id, _ in expected})
node_rows = (
    graph["nodes"]
    .filter(F.col("ELEMENT_PATH") == F.lit(requirement_path))
    .filter(F.col("SOURCE_RECORD_ID").isin(*parents))
    .select("SOURCE_RECORD_ID", "INSTANCE_KEY", "OSCAL_UUID", "METADATA_JSON")
    .collect()
)
candidate = {}
for row in node_rows:
    pair = (str(row["SOURCE_RECORD_ID"]), str(row["INSTANCE_KEY"]))
    if pair in expected:
        if pair in candidate:
            raise ValueError("Candidate graph has duplicate requirement identities.")
        candidate[pair] = row

# Use the candidate UUID exactly as produced by Cell 5, not an independently
# recreated UUID seed. The physical target stores UUIDs without hyphens.
candidate_uuids = sorted({
    str(node["OSCAL_UUID"]).replace("-", "")
    for node in candidate.values()
})
persisted = {}
if candidate_uuids:
    target_rows = (
        session.table(storage["TARGET_DIM"])
        .filter(F.col("OSCAL_UUID").isin(*candidate_uuids))
        .select(
            "OSCAL_UUID", "SOURCE_RECORD_ID", "SOURCE_SYSTEM_NAME",
            "SOURCE_TABLE_NAME", "ELEMENT_TYPE", "METADATA_JSON",
        )
        .collect()
    )
    for row in target_rows:
        uid = str(row["OSCAL_UUID"])
        if uid in persisted:
            raise ValueError("Duplicate persisted requirement UUID.")
        persisted[uid] = row

def object_payload(value):
    decoded = json.loads(value) if isinstance(value, str) else _to_python(value)
    if not isinstance(decoded, dict):
        raise ValueError("Expected an object-valued OSCAL payload.")
    return decoded

issues = []
control_matches = 0
remarks_matches = 0
graph_value_matches = 0
source_to_graph_missing = 0
persisted_missing = 0
for pair, source in expected.items():
    node = candidate.get(pair)
    if node is None:
        source_to_graph_missing += 1
        issues.append({"SOURCE_CHILD_ID": source["child_id"], "ISSUE": "MISSING_CANDIDATE_NODE"})
        continue

    candidate_payload = object_payload(node["METADATA_JSON"])
    if not all(candidate_payload.get(k) == source[k] for k in required_members):
        issues.append({"SOURCE_CHILD_ID": source["child_id"], "ISSUE": "SOURCE_TO_GRAPH_VALUE_MISMATCH"})
        continue
    graph_value_matches += 1

    uuid32 = str(node["OSCAL_UUID"]).replace("-", "")
    saved = persisted.get(uuid32)
    if saved is None:
        persisted_missing += 1
        issues.append({"SOURCE_CHILD_ID": source["child_id"], "ISSUE": "MISSING_PERSISTED_TARGET"})
        continue

    provenance_ok = (
        str(saved["SOURCE_RECORD_ID"]) == pair[0]
        and saved["SOURCE_SYSTEM_NAME"] == cfg["SOURCE_SYSTEM_NAME"]
        and saved["SOURCE_TABLE_NAME"] == cfg["SOURCE_TABLE_NAME"]
        and saved["ELEMENT_TYPE"] == "implemented-requirements"
    )
    target_payload = object_payload(saved["METADATA_JSON"])
    id_ok = provenance_ok and target_payload.get("control-id") == source["control-id"]
    remarks_ok = provenance_ok and target_payload.get("remarks") == source["remarks"]
    control_matches += int(id_ok)
    remarks_matches += int(remarks_ok)
    if not (id_ok and remarks_ok):
        issues.append({
            "SOURCE_CHILD_ID": source["child_id"],
            "ISSUE": "PERSISTED_VALUE_OR_PROVENANCE_MISMATCH",
            "CONTROL_ID_MATCH": id_ok,
            "REMARKS_MATCH": remarks_ok,
        })

summary = {
    "SAMPLED_SOURCE_PACKAGES": len(expected),
    "SAMPLED_REQUIREMENTS": len(expected),
    "SOURCE_TO_GRAPH_VALUE_MATCHES": graph_value_matches,
    "SOURCE_TO_GRAPH_MISSING": source_to_graph_missing,
    "PERSISTED_TARGET_MISSING": persisted_missing,
    "CONTROL_ID_VALUE_MATCHES": control_matches,
    "REMARKS_VALUE_MATCHES": remarks_matches,
    "MISMATCHES": len(issues),
    "STATUS": "SAMPLE_VERIFIED" if not issues and len(expected) == MAX_SAMPLES else "REVIEW_REQUIRED",
}
print("IMPLEMENTED REQUIREMENTS SOURCE-TO-TARGET SAMPLE QA")
print(json.dumps(summary, indent=2))
if issues:
    print("FIRST_ISSUES (IDs and statuses only; no source values)")
    print(json.dumps(issues[:10], indent=2))
```

Interpretation: `SAMPLE_VERIFIED` requires 15 distinct populated source packages, matching candidate graph values, and matching persisted values with no reported issues. The summary separates missing candidate nodes from missing persisted UUIDs, avoiding misleading all-or-nothing "missing target" claims.

This is a **sample**, not full-source coverage, complete Level-355 row parity, or an OSCAL schema validation. No DML, DDL, pipeline reload, or mapper COMMIT is required.
