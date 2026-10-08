# Control Implementation — original source field -> actual persisted OSCAL value
# ONE CELL. Run in the existing Snowflake Python notebook after the SSP mapper
# has populated MODEL_GRAPHS. No table names, CSV stages, or variables to edit.
# Read-only target SQL; no merge, DML, DDL, or mapper rerun.

if "MODEL_GRAPHS" not in globals() or "session" not in globals():
    raise RuntimeError("Use the existing loaded SSP mapper notebook session.")

ssp_routes = [
    key for key in MODEL_GRAPHS
    if isinstance(key, tuple) and len(key) == 2 and key[1] == "SSP"
]
if len(ssp_routes) != 1:
    raise RuntimeError("One SSP graph must already be loaded in this notebook.")

ctx = MODEL_GRAPHS[ssp_routes[0]]["context"]
cfg = ctx["config"]
storage = cfg["STORAGE_CONTRACT"]

property_path = "system-security-plan.system-characteristics.props[]"
assessor_path = "system-security-plan.metadata.responsible-parties[]"
requirement_path = "system-security-plan.control-implementation.implemented-requirements[]"

selected = [
    row for row in ctx["mapping_rows"]
    if row.get("ARTIFACT_MODEL") == "SSP - Control Implementation"
    and row.get("APPROVAL_STATUS") == "APPROVED"
]

if not selected:
    raise RuntimeError("No approved Control Implementation mappings in loaded SSP.")
if len({row["SOURCE_FIELD_NAME"] for row in selected}) != len(selected):
    raise RuntimeError("Duplicate source field mappings require manual review.")

def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"

bindings = []
for mapping in selected:
    owner = mapping["OWNER_ELEMENT_PATH"]
    operator = mapping["REPRESENTATION"]
    params = mapping.get("REPRESENTATION_PARAMS") or {}
    field = mapping["SOURCE_FIELD_NAME"]

    if owner == property_path and operator == "properties":
        kind = "PACKAGE_PROP"
        member = params.get("property_name") or _stable_property_name(field)
    elif owner == assessor_path and operator == "assignments":
        kind = "ASSESSOR_ROLE"
        member = params["role_id"]
    elif owner == requirement_path and operator == "joined-records":
        kind = "REQUIREMENT_MEMBER"
        member = params.get("target") or mapping.get("FIELD_RELATIVE_PATH")
        if not member:
            raise RuntimeError("Missing native requirement member target.")
    else:
        raise RuntimeError("Unexpected approved Control Implementation target: " + owner)

    if kind == "REQUIREMENT_MEMBER":
        binding = params["joined_lookup"]
        origin_table = ctx["lookups"]["joined_contract"][binding]["source_table"]
    else:
        origin_table = cfg["RAW_TABLE"]

    bindings.append((
        field,
        kind,
        origin_table,
        mapping["OSCAL_ELEMENT_PATH"],
        member
    ))

dim = storage["TARGET_DIM"]
fact = storage["TARGET_FACT"]
pk = storage["DIM_PK_COLUMN"]
source_system = sql_literal(cfg["SOURCE_SYSTEM_NAME"])
source_table = sql_literal(cfg["SOURCE_TABLE_NAME"])
value_rows = ",\n".join(
    "(" + ", ".join(sql_literal(value) for value in binding) + ")"
    for binding in bindings
)

# Source field names, their correct target paths, and all physical table
# references are taken from the already-loaded runtime, not hardcoded.
read_only_sql = f"""
WITH mapping_fields (ARCHER_SQL_FIELD, SOURCE_SCOPE, ARCHER_SOURCE_TABLE,
                     OSCAL_TARGET_PATH, TARGET_MEMBER) AS (
    SELECT column1::STRING, column2::STRING, column3::STRING,
           column4::STRING, column5::STRING
    FROM VALUES
    {value_rows}
),
stored_values AS (
    SELECT m.ARCHER_SQL_FIELD, sc.SOURCE_RECORD_ID,
           p.OSCAL_UUID AS TARGET_OSCAL_UUID,
           p.METADATA_JSON:"value" AS OSCAL_VALUE
    FROM {dim} sc
    JOIN {fact} e
      ON e.FK_SOURCE_ELEMENT_HASH = sc.{pk}
     AND e.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN {dim} p
      ON p.{pk} = e.FK_TARGET_ELEMENT_HASH
    JOIN mapping_fields m
      ON m.SOURCE_SCOPE = 'PACKAGE_PROP'
     AND p.METADATA_JSON:"name"::STRING = m.TARGET_MEMBER
    WHERE sc.ELEMENT_TYPE = 'system-characteristics'
      AND p.ELEMENT_TYPE = 'props'
      AND sc.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID
      AND sc.SOURCE_SYSTEM_NAME = {source_system}
      AND sc.SOURCE_TABLE_NAME = {source_table}

    UNION ALL

    SELECT m.ARCHER_SQL_FIELD, rp.SOURCE_RECORD_ID,
           rp.OSCAL_UUID AS TARGET_OSCAL_UUID,
           rp.METADATA_JSON:"party-uuids" AS OSCAL_VALUE
    FROM {dim} md
    JOIN {fact} e
      ON e.FK_SOURCE_ELEMENT_HASH = md.{pk}
     AND e.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN {dim} rp
      ON rp.{pk} = e.FK_TARGET_ELEMENT_HASH
    JOIN mapping_fields m
      ON m.SOURCE_SCOPE = 'ASSESSOR_ROLE'
     AND rp.METADATA_JSON:"role-id"::STRING = m.TARGET_MEMBER
    WHERE md.ELEMENT_TYPE = 'metadata'
      AND rp.ELEMENT_TYPE = 'responsible-parties'
      AND md.SOURCE_RECORD_ID = rp.SOURCE_RECORD_ID
      AND md.SOURCE_SYSTEM_NAME = {source_system}
      AND md.SOURCE_TABLE_NAME = {source_table}

    UNION ALL

    SELECT m.ARCHER_SQL_FIELD, ir.SOURCE_RECORD_ID,
           ir.OSCAL_UUID AS TARGET_OSCAL_UUID,
           GET(ir.METADATA_JSON, m.TARGET_MEMBER) AS OSCAL_VALUE
    FROM {dim} ir
    JOIN mapping_fields m
      ON m.SOURCE_SCOPE = 'REQUIREMENT_MEMBER'
    WHERE ir.ELEMENT_TYPE = 'implemented-requirements'
      AND ir.SOURCE_SYSTEM_NAME = {source_system}
      AND ir.SOURCE_TABLE_NAME = {source_table}
),
ranked AS (
    SELECT v.*,
           ROW_NUMBER() OVER (
             PARTITION BY v.ARCHER_SQL_FIELD
             ORDER BY IFF(
                 v.OSCAL_VALUE IS NOT NULL
                 AND NOT IS_NULL_VALUE(v.OSCAL_VALUE), 0, 1
             ), v.SOURCE_RECORD_ID, v.TARGET_OSCAL_UUID
           ) AS SAMPLE_NUMBER
    FROM stored_values v
)
SELECT m.ARCHER_SQL_FIELD,
       m.ARCHER_SOURCE_TABLE,
       m.OSCAL_TARGET_PATH,
       r.SOURCE_RECORD_ID,
       r.OSCAL_VALUE,
       CASE
         WHEN r.SOURCE_RECORD_ID IS NULL THEN 'NO_PERSISTED_EXAMPLE'
         WHEN r.OSCAL_VALUE IS NULL OR IS_NULL_VALUE(r.OSCAL_VALUE)
           THEN 'NULL_VALUE'
         ELSE 'POPULATED_VALUE'
       END AS VALUE_STATUS
FROM mapping_fields m
LEFT JOIN ranked r
  ON r.ARCHER_SQL_FIELD = m.ARCHER_SQL_FIELD
 AND r.SAMPLE_NUMBER <= 3
ORDER BY m.ARCHER_SQL_FIELD, r.SAMPLE_NUMBER
"""

print("CONTROL IMPLEMENTATION — ORIGINAL ARCHER FIELDS AND STORED VALUES")
print("Approved mappings found:", len(bindings))
print("Source names / paths / target tables: loaded from existing mapper context")
results = session.sql(read_only_sql)
results.show(n=max(3 * len(bindings), 100), max_width=220)
