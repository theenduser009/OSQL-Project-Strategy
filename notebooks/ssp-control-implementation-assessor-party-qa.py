# Read-only SSP Control Implementation responsible-party QA.
# Run after the mapper with MODEL_GRAPHS and SOURCE_INPUTS in the same Snowflake
# session. Derives all source fields, roles and target table bindings from the
# currently compiled mapping. No changes to Snowflake data or schema.
import uuid
import json
from collections import defaultdict

# In reused notebook sessions, an earlier QA loop may assign a string named
# 'uuid'. Restore the standard-library module in the mapper helper's own
# global namespace before creating deterministic party UUIDs.
_deterministic_uuid.__globals__["uuid"] = uuid

OWNER_PATH = "system-security-plan.metadata.responsible-parties[]"
MAPPING_GROUP = "SSP - Control Implementation"
MAX_ISSUES = 10

if not globals().get("MODEL_GRAPHS") or not globals().get("SOURCE_INPUTS"):
    raise ValueError("Load the existing SSP mapper context before QA.")
routes = [
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
]
if len(routes) != 1:
    raise ValueError("Exactly one SSP route must be loaded.")
route = routes[0]
ctx = MODEL_GRAPHS[route]["context"]
cfg = ctx["config"]
storage = cfg["STORAGE_CONTRACT"]

mapping_rows = [
    row for row in ctx["mapping_rows"]
    if row.get("ARTIFACT_MODEL") == MAPPING_GROUP
    and row.get("OWNER_ELEMENT_PATH") == OWNER_PATH
    and row.get("REPRESENTATION") == "assignments"
]
if len(mapping_rows) != 2:
    raise ValueError("Expected exactly two approved assessor-role mapping rows.")
by_role = {}
for row in mapping_rows:
    role = (row.get("REPRESENTATION_PARAMS") or {}).get("role_id")
    if not role or role in by_role or not row.get("LINEAGE_REQUIRED_FLAG"):
        raise ValueError("Assessor mapping needs a unique role and approved lineage.")
    by_role[role] = row

# Derive expected references from the exact retained Archer source snapshot,
# using the SAME extraction, stable-identifier and UUID policy as the mapper.
qa_ctx = dict(ctx)
qa_ctx["graph_report"] = {
    "STATUS": "NOT_RUN", "MAPPED_VALUES": 0, "MISSING_VALUES": 0
}
expected = {}  # (parent SOURCE_RECORD_ID, role) -> unique party UUIDs
source_stats = defaultdict(lambda: {
    "source_present": 0, "source_populated": 0,
    "explicit_null": 0, "empty_selections": 0,
    "mappable_records": 0, "source_references": 0
})
source_ids = set()
issues = []

for record in SOURCE_INPUTS[route[0]]["source_df"].to_local_iterator():
    rid = str(record["SOURCE_RECORD_ID"])
    if rid in source_ids:
        raise ValueError("Duplicate source record identity.")
    source_ids.add(rid)
    source_obj = _metadata_parse(record, ctx)

    for role, mapping in by_role.items():
        stats = source_stats[role]
        raw = resolve_json_path(
            source_obj, mapping["SOURCE_FIELD_NAME"], default=SKIP_VALUE
        )
        if raw is not SKIP_VALUE:
            stats["source_present"] += 1
        if raw is None:
            stats["explicit_null"] += 1
        if raw is not SKIP_VALUE and _has_value(raw):
            stats["source_populated"] += 1

        try:
            value = _metadata_mapped_value(mapping, source_obj, qa_ctx)
            if value is SKIP_VALUE:
                continue
            if (
                isinstance(value, dict)
                and {"UserList", "GroupList"}.intersection(value)
                and value.get("UserList", []) == []
                and value.get("GroupList", []) == []
            ):
                stats["empty_selections"] += 1
                continue

            extracted = _extract_reference_ids(value)
            members = extracted if isinstance(extracted, list) else [extracted]
            uuids = set()
            for item in members:
                if item is None:
                    continue
                identifier = _party_reference_identifier(item)
                uuids.add(_deterministic_uuid(
                    cfg["SOURCE_SYSTEM_NAME"], rid, "party", identifier
                ))
            if uuids:
                expected[(rid, role)] = uuids
                stats["mappable_records"] += 1
                stats["source_references"] += len(uuids)
        except (TypeError, ValueError, ArithmeticError) as exc:
            issues.append({
                "ROLE_ID": role, "ISSUE": "SOURCE_" + type(exc).__name__
            })

# Query persisted nodes through actual parent metadata -> FACT -> child edges.
# A matching role anywhere else in the SSP graph is NOT sufficient.
def q(value):
    return "'" + str(value).replace("'", "''") + "'"

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
pk = storage["DIM_PK_COLUMN"]
source_system = q(cfg["SOURCE_SYSTEM_NAME"])
source_table = q(cfg["SOURCE_TABLE_NAME"])
role_list = ", ".join(q(role) for role in sorted(by_role))

sql = f"""
SELECT child.SOURCE_RECORD_ID AS SOURCE_RECORD_ID,
       child.ELEMENT_TYPE AS ELEMENT_TYPE,
       TO_JSON(child.METADATA_JSON) AS PAYLOAD
FROM {dim} parent
JOIN {fact} edge
  ON edge.FK_SOURCE_ELEMENT_HASH = parent.{pk}
 AND edge.DEPENDENCY_TYPE = 'CONTAINS'
JOIN {dim} child
  ON child.{pk} = edge.FK_TARGET_ELEMENT_HASH
WHERE parent.ELEMENT_TYPE = 'metadata'
  AND child.ELEMENT_TYPE IN ('responsible-parties', 'parties')
  AND parent.SOURCE_SYSTEM_NAME = {source_system}
  AND parent.SOURCE_TABLE_NAME = {source_table}
  AND child.SOURCE_SYSTEM_NAME = {source_system}
  AND child.SOURCE_TABLE_NAME = {source_table}
  AND child.SOURCE_RECORD_ID = parent.SOURCE_RECORD_ID
"""

actual_roles = defaultdict(list)
actual_parties = defaultdict(list)
for row in session.sql(sql).to_local_iterator():
    rid = str(row["SOURCE_RECORD_ID"])
    payload = json.loads(row["PAYLOAD"])
    if not isinstance(payload, dict):
        issues.append({"ISSUE": "NON_OBJECT_PERSISTED_PAYLOAD"})
        continue
    if rid not in source_ids:
        issues.append({"ISSUE": "EXTRA_SOURCE_RECORD_IN_TARGET"})
    if row["ELEMENT_TYPE"] == "responsible-parties":
        role = payload.get("role-id")
        if role in by_role:
            actual_roles[(rid, role)].append(payload)
    else:
        party_uuid = payload.get("uuid")
        if party_uuid:
            actual_parties[(rid, party_uuid)].append(payload)

results = []
for role, mapping in sorted(by_role.items()):
    role_keys = {
        key for key in set(expected) | set(actual_roles) if key[1] == role
    }
    failures = 0
    matched = 0
    target_rows = 0
    for key in sorted(role_keys):
        rid = key[0]
        uuids = expected.get(key, set())
        assignments = actual_roles.get(key, [])
        target_rows += len(assignments)

        if not uuids or len(assignments) != 1:
            failures += 1
            issues.append({"ROLE_ID": role, "ISSUE": "MISSING_EXTRA_OR_DUPLICATE_ROLE"})
            continue
        payload = assignments[0]
        saved_uuids = payload.get("party-uuids")
        props = payload.get("props", [])
        if not isinstance(saved_uuids, list) or not isinstance(props, list):
            failures += 1
            issues.append({"ROLE_ID": role, "ISSUE": "INVALID_ASSIGNMENT_PAYLOAD"})
            continue

        lineage = [
            p.get("value") for p in props
            if isinstance(p, dict) and p.get("name") == "source-field"
        ]
        party_ok = all(
            len(actual_parties.get((rid, party_uuid), [])) == 1
            for party_uuid in uuids
        )
        ok = (
            len(saved_uuids) == len(uuids)
            and set(saved_uuids) == uuids
            and lineage == [mapping["SOURCE_FIELD_NAME"]]
            and party_ok
        )
        if ok:
            matched += 1
        else:
            failures += 1
            issues.append({
                "ROLE_ID": role,
                "ISSUE": "PARTY_UUID_OR_SOURCE_FIELD_LINEAGE_MISMATCH"
            })

    stats = source_stats[role]
    if failures:
        status = "REVIEW_REQUIRED"
    elif stats["mappable_records"] == 0:
        status = "NO_MAPPABLE_SOURCE_REFERENCES"
    else:
        status = "SOURCE_TO_TARGET_REFERENCES_VERIFIED"
    results.append({
        "SOURCE_FIELD_NAME": mapping["SOURCE_FIELD_NAME"],
        "ROLE_ID": role,
        **stats,
        "PERSISTED_ASSIGNMENT_ROWS": target_rows,
        "MATCHED_ASSIGNMENT_RECORDS": matched,
        "MISMATCH_RECORDS": failures,
        "STATUS": status
    })

summary = {
    "MAPPING_ROWS": len(mapping_rows),
    "SOURCE_RECORDS": len(source_ids),
    "POPULATED_ROLE_FIELDS_VERIFIED": sum(
        x["STATUS"] == "SOURCE_TO_TARGET_REFERENCES_VERIFIED" for x in results
    ),
    "NO_MAPPABLE_SOURCE_FIELDS": sum(
        x["STATUS"] == "NO_MAPPABLE_SOURCE_REFERENCES" for x in results
    ),
    "MISMATCH_RECORDS": sum(x["MISMATCH_RECORDS"] for x in results),
    "OTHER_QA_ISSUES": len(issues) - sum(x["MISMATCH_RECORDS"] for x in results),
    "STATUS": "VERIFIED" if not issues else "REVIEW_REQUIRED"
}
print("CONTROL IMPLEMENTATION ASSESSOR RESPONSIBLE-PARTY QA")
print(json.dumps(summary, indent=2))
print("FIELD RESULTS")
for item in results:
    print(json.dumps(item))
if issues:
    print("FIRST ISSUES (role/type only; no source values)")
    print(json.dumps(issues[:MAX_ISSUES], indent=2))
