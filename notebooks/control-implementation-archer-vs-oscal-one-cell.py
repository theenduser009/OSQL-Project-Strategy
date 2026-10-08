# Read-only Source One / SSP Control Implementation package property trace.
# One Python cell in an ALREADY-LOADED Snowflake SSP mapper notebook.
# No parameter values, table names, CSV stages, or record IDs to enter.
# Every approved package-property name is taken from the compiled mapping.
# Shows original source JSON vs actual persisted OSCAL prop members.
import json

if "MODEL_GRAPHS" not in globals() or "SOURCE_INPUTS" not in globals():
    raise RuntimeError("Run in your existing loaded SSP mapper notebook.")
routes = [k for k in MODEL_GRAPHS if isinstance(k, tuple)
          and len(k) == 2 and k[1] == "SSP"]
if len(routes) != 1 or routes[0][0] not in SOURCE_INPUTS:
    raise RuntimeError("Expected one loaded SSP source route.")

route = routes[0]
ctx = MODEL_GRAPHS[route]["context"]
cfg = ctx["config"]
storage = cfg["STORAGE_CONTRACT"]
owner_path = "system-security-plan.system-characteristics.props[]"
mappings = [
    m for m in ctx["mapping_rows"]
    if m.get("ARTIFACT_MODEL") == "SSP - Control Implementation"
    and m.get("APPROVAL_STATUS") == "APPROVED"
    and m.get("OWNER_ELEMENT_PATH") == owner_path
    and m.get("REPRESENTATION") == "properties"
]
if not mappings:
    raise RuntimeError("No approved package property mappings found.")

def name_for(m):
    return (_metadata_params(m).get("property_name")
            or _stable_property_name(m["SOURCE_FIELD_NAME"]))

if len(set(name_for(m) for m in mappings)) != len(mappings):
    raise RuntimeError("Ambiguous property names; cannot infer a source field.")

# Pick one source-snapshot example for each approved business property.
# Prefer actual populated source data; otherwise preserve a null-only sample.
qa_ctx = dict(ctx)
qa_ctx["graph_report"] = {"STATUS": "NOT_RUN",
                          "MAPPED_VALUES": 0, "MISSING_VALUES": 0}
chosen = {}
for record in SOURCE_INPUTS[route[0]]["source_df"].to_local_iterator():
    rid = str(record["SOURCE_RECORD_ID"])
    source = _metadata_parse(record, ctx)
    for mapping in mappings:
        field = mapping["SOURCE_FIELD_NAME"]
        if field in chosen and chosen[field]["priority"] == 0:
            continue
        raw = resolve_json_path(source, field, default=SKIP_VALUE)
        if raw is SKIP_VALUE:
            continue
        mapped = _metadata_mapped_value(mapping, source, qa_ctx)
        if mapped is SKIP_VALUE:
            continue
        expected = [None] if mapped is None else _oscal_property_values(mapped)
        if not expected:
            continue
        priority = 0 if any(v is not None for v in expected) else 1
        if field not in chosen or priority < chosen[field]["priority"]:
            chosen[field] = {
                "source_id": rid,
                "raw": _to_python(raw),
                "expected": expected,
                "priority": priority
            }

def sql_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

ids = sorted(set(v["source_id"] for v in chosen.values()))
names = sorted(set(name_for(m) for m in mappings))
actual = {}
if ids:
    dim = storage["TARGET_DIM"]
    fact = storage["TARGET_FACT"]
    pk = storage["DIM_PK_COLUMN"]
    id_list = ", ".join(sql_quote(v) for v in ids)
    name_list = ", ".join(sql_quote(v) for v in names)
    sql = f"""
        SELECT sc.SOURCE_RECORD_ID, TO_JSON(p.METADATA_JSON) AS PROP_JSON
        FROM {dim} sc
        JOIN {fact} e
          ON e.FK_SOURCE_ELEMENT_HASH = sc.{pk}
         AND e.DEPENDENCY_TYPE = 'CONTAINS'
        JOIN {dim} p
          ON p.{pk} = e.FK_TARGET_ELEMENT_HASH
        WHERE sc.ELEMENT_TYPE = 'system-characteristics'
          AND p.ELEMENT_TYPE = 'props'
          AND sc.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID
          AND sc.SOURCE_SYSTEM_NAME = {sql_quote(cfg["SOURCE_SYSTEM_NAME"])}
          AND sc.SOURCE_TABLE_NAME = {sql_quote(cfg["SOURCE_TABLE_NAME"])}
          AND p.SOURCE_SYSTEM_NAME = sc.SOURCE_SYSTEM_NAME
          AND p.SOURCE_TABLE_NAME = sc.SOURCE_TABLE_NAME
          AND sc.SOURCE_RECORD_ID IN ({id_list})
          AND p.METADATA_JSON:"name"::STRING IN ({name_list})
    """
    for saved in session.sql(sql).to_local_iterator():
        payload = json.loads(saved["PROP_JSON"])
        key = (str(saved["SOURCE_RECORD_ID"]), payload["name"])
        actual.setdefault(key, []).append(payload.get("value"))

def normalized(values):
    return sorted(json.dumps(v, sort_keys=True, default=str) for v in values)

print("CONTROL IMPLEMENTATION: ORIGINAL ARCHER VALUE -> OSCAL PROPERTY")
print("Approved package property mappings:", len(mappings))
print("One source-snapshot example per field, populated examples preferred.")
for mapping in sorted(mappings, key=lambda m: m["SOURCE_FIELD_NAME"]):
    field = mapping["SOURCE_FIELD_NAME"]
    prop_name = name_for(mapping)
    sample = chosen.get(field)
    if sample is None:
        result = {
            "ARCHER_FIELD": field,
            "OSCAL_PROPERTY": prop_name,
            "STATUS": "NO_MAPPABLE_SOURCE_EXAMPLE"
        }
    else:
        stored = actual.get((sample["source_id"], prop_name), [])
        agrees = normalized(sample["expected"]) == normalized(stored)
        result = {
            "ARCHER_FIELD": field,
            "PACKAGE_CONTENT_ID": sample["source_id"],
            "ARCHER_SOURCE_VALUE": sample["raw"],
            "OSCAL_PROPERTY": prop_name,
            "OSCAL_STORED_VALUES": stored,
            "STATUS": (
                "POPULATED_VALUE_MATCH" if agrees and sample["priority"] == 0
                else "NULL_ONLY_MATCH" if agrees
                else "REVIEW_REQUIRED"
            )
        }
    print(json.dumps(result, default=str, ensure_ascii=False))
