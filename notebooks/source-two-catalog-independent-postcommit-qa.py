# Source Two Catalog: independent read-only post-commit integrity check.
# One new PYTHON cell in the maintained Snowflake mapping notebook.
# Uses the universal Cell 1 SOURCE_FILES and MODEL_CONTRACTS runtime config.
# Does NOT rerun the mapper or write any source/DIM/FACT tables.
# Six historical-size checks are informational, not hardcoded baselines;
# the other 15 checks verify current source IDs, tracking values and graph integrity.

import csv

required = ("session", "SOURCE_FILES", "MODEL_CONTRACTS")
missing = [name for name in required if name not in globals()]
if missing:
    raise RuntimeError("Open the maintained mapper notebook and run its Cell 1 first: "
                       + ", ".join(missing))

sources = [s for s in SOURCE_FILES if "CATALOG" in s.get("MODEL_BINDINGS", ())]
if len(sources) != 1:
    raise RuntimeError("Expected exactly one Source Two Catalog source in Cell 1.")
profile = sources[0]
contract = MODEL_CONTRACTS["CATALOG"]["STORAGE_CONTRACT"]

loaded_mappings = globals().get("MAPPING_INPUTS", {}).get(profile["SOURCE_KEY"])
if loaded_mappings is None:
    try:
        with open(profile["MAPPING_FILE"], encoding=profile.get("MAPPING_ENCODING", "utf-8-sig"),
                  newline="") as fh:
            loaded_mappings = list(csv.DictReader(fh))
    except OSError as exc:
        raise RuntimeError(
            "Source Two mapping file is not loaded in this notebook. "
            "Load the Source Two Catalog inputs with Cells 1-2, in read-only mode."
        ) from exc

matching = [m for m in loaded_mappings
            if m.get("EXECUTION_STATUS") == "APPROVED"
            and m.get("OSCAL_MODEL", "").startswith("Catalog")
            and m.get("PROPERTY_NAME", "").strip() == "tracking-id"
            and m.get("SOURCE_FIELD_NAME")]
names = set(m["SOURCE_FIELD_NAME"] for m in matching)
if len(names) != 1:
    raise RuntimeError("Cannot uniquely resolve current Catalog tracking-id source field.")
tracking_field = next(iter(names))

def identifier(v):
    import re
    if not re.fullmatch(r"[A-Za-z0-9_$]+(?:\.[A-Za-z0-9_$]+){0,2}", str(v)):
        raise RuntimeError("Unsafe object identifier in existing Cell 1 configuration.")
    return str(v)

def literal(v):
    return str(v).replace("'", "''")

sql = r'''WITH
source_payloads AS (
    SELECT CAST(CONTENT_ID AS VARCHAR) AS SOURCE_RECORD_ID,
           CASE WHEN TYPEOF(CURATED_JSON)='VARCHAR'
                THEN TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON))
                ELSE CURATED_JSON END AS PAYLOAD
    FROM __SOURCE_TABLE__
),
source_rows AS (
    SELECT SOURCE_RECORD_ID, PAYLOAD, GET(PAYLOAD,'__TRACKING_FIELD__') AS RAW_TRACKING,
           COUNT(*) OVER (PARTITION BY SOURCE_RECORD_ID) AS ROWS_PER_ID
    FROM source_payloads
),
source_valid AS (
    SELECT SOURCE_RECORD_ID, TRIM(TO_VARCHAR(RAW_TRACKING)) AS EXPECTED_VALUE
    FROM source_rows
    WHERE ROWS_PER_ID=1 AND SOURCE_RECORD_ID IS NOT NULL
      AND TRIM(SOURCE_RECORD_ID)<>'' AND SOURCE_RECORD_ID=TRIM(SOURCE_RECORD_ID)
      AND COALESCE(IS_OBJECT(PAYLOAD),FALSE)
      AND TYPEOF(RAW_TRACKING) IN ('INTEGER','VARCHAR')
      AND TRIM(TO_VARCHAR(RAW_TRACKING))<>''
),
d AS (
    SELECT PK_DIM_OSCAL_CATALOG_ELEMENT_HASH AS NODE_KEY, ELEMENT_TYPE, OSCAL_UUID,
           SOURCE_SYSTEM_NAME, SOURCE_TABLE_NAME, SOURCE_RECORD_ID, METADATA_JSON
    FROM __DIM_TABLE__
),
f AS (
    SELECT PK_FACT_OSCAL_CATALOG_DEPENDENCY_HASH AS FACT_KEY,
           FK_SOURCE_ELEMENT_HASH, FK_TARGET_ELEMENT_HASH, DEPENDENCY_TYPE,
           SOURCE_OSCAL_UUID, TARGET_OSCAL_UUID
    FROM __FACT_TABLE__
),
key_defects AS (
    SELECT 'DIM_PK' AS KEY_KIND FROM d GROUP BY NODE_KEY
    HAVING NODE_KEY IS NULL OR COUNT(*)>1
    UNION ALL SELECT 'FACT_PK' FROM f GROUP BY FACT_KEY
    HAVING FACT_KEY IS NULL OR COUNT(*)>1
    UNION ALL SELECT 'DIM_UUID' FROM d GROUP BY OSCAL_UUID
    HAVING OSCAL_UUID IS NULL OR TRIM(OSCAL_UUID)='' OR COUNT(*)>1
),
record_nodes AS (
    SELECT SOURCE_RECORD_ID,
           SUM(CASE WHEN ELEMENT_TYPE='catalog' THEN 1 ELSE 0 END) AS ROOTS,
           SUM(CASE WHEN ELEMENT_TYPE='metadata' THEN 1 ELSE 0 END) AS METADATA_ROWS
    FROM d GROUP BY SOURCE_RECORD_ID
),
parent_counts AS (
    SELECT d.NODE_KEY, d.ELEMENT_TYPE, COUNT(f.FK_TARGET_ELEMENT_HASH) AS PARENTS
    FROM d LEFT JOIN f ON f.FK_TARGET_ELEMENT_HASH=d.NODE_KEY
    GROUP BY d.NODE_KEY, d.ELEMENT_TYPE
),
joined_edges AS (
    SELECT f.*, s.ELEMENT_TYPE AS SOURCE_TYPE, t.ELEMENT_TYPE AS TARGET_TYPE,
           s.OSCAL_UUID AS PARENT_UUID, t.OSCAL_UUID AS CHILD_UUID,
           s.SOURCE_SYSTEM_NAME AS PARENT_SYSTEM, t.SOURCE_SYSTEM_NAME AS CHILD_SYSTEM,
           s.SOURCE_TABLE_NAME AS PARENT_TABLE, t.SOURCE_TABLE_NAME AS CHILD_TABLE,
           s.SOURCE_RECORD_ID AS PARENT_RECORD, t.SOURCE_RECORD_ID AS CHILD_RECORD
    FROM f JOIN d s ON s.NODE_KEY=f.FK_SOURCE_ELEMENT_HASH
           JOIN d t ON t.NODE_KEY=f.FK_TARGET_ELEMENT_HASH
),
tracking AS (
    SELECT d.*, GET(METADATA_JSON,'value') AS PROPERTY_VALUE
    FROM d WHERE ELEMENT_TYPE='props'
      AND AS_VARCHAR(GET(METADATA_JSON,'name'))='tracking-id'
),
tracking_counts AS (
    SELECT SOURCE_RECORD_ID, COUNT(*) AS PROPERTY_ROWS
    FROM tracking GROUP BY SOURCE_RECORD_ID
),
tracking_comparison AS (
    SELECT s.SOURCE_RECORD_ID, s.EXPECTED_VALUE, t.PROPERTY_VALUE
    FROM source_valid s JOIN tracking_counts c ON c.SOURCE_RECORD_ID=s.SOURCE_RECORD_ID
    JOIN tracking t ON t.SOURCE_RECORD_ID=s.SOURCE_RECORD_ID
    WHERE c.PROPERTY_ROWS=1
),
checks AS (
    SELECT 1 AS CHECK_ORDER, 'SOURCE_ROWS' AS QA_CHECK,
           (SELECT COUNT(*) FROM source_rows) AS OBSERVED_COUNT, NULL AS EXPECTED_COUNT, 'INFO' AS CHECK_KIND
    UNION ALL
    SELECT 2, 'CATALOG_DIM_ROWS',
           (SELECT COUNT(*) FROM d), NULL, 'INFO'
    UNION ALL
    SELECT 3, 'CATALOG_FACT_ROWS',
           (SELECT COUNT(*) FROM f), NULL, 'INFO'
    UNION ALL
    SELECT 4, 'CATALOG_ROOT_ROWS',
           (SELECT COUNT(*) FROM d WHERE ELEMENT_TYPE='catalog'), NULL, 'INFO'
    UNION ALL
    SELECT 5, 'TRACKING_ID_PROPERTY_ROWS',
           (SELECT COUNT(*) FROM tracking), NULL, 'INFO'
    UNION ALL
    SELECT 6, 'MATCHED_TRACKING_IDS',
           (SELECT COUNT(*) FROM tracking_comparison WHERE AS_VARCHAR(PROPERTY_VALUE)=EXPECTED_VALUE), NULL, 'INFO'
    UNION ALL
    SELECT 7, 'INVALID_OR_DUPLICATE_SOURCE_ID_GROUPS',
           (SELECT COUNT(*) FROM (SELECT SOURCE_RECORD_ID FROM source_rows GROUP BY SOURCE_RECORD_ID HAVING SOURCE_RECORD_ID IS NULL OR TRIM(SOURCE_RECORD_ID)='' OR SOURCE_RECORD_ID<>TRIM(SOURCE_RECORD_ID) OR COUNT(*)<>1) q), 0, 'INPUT'
    UNION ALL
    SELECT 8, 'SOURCE_TRACKING_INPUTS_NEEDING_REVIEW',
           (SELECT COUNT(*) FROM source_rows WHERE NOT COALESCE(IS_OBJECT(PAYLOAD),FALSE) OR NOT COALESCE(TYPEOF(RAW_TRACKING) IN ('INTEGER','VARCHAR'),FALSE) OR COALESCE(TRIM(TO_VARCHAR(RAW_TRACKING)),'')=''), 0, 'INPUT'
    UNION ALL
    SELECT 9, 'NULL_OR_DUPLICATE_TARGET_KEY_GROUPS',
           (SELECT COUNT(*) FROM key_defects), 0, 'DEFECT'
    UNION ALL
    SELECT 10, 'INVALID_TARGET_OWNERSHIP_OR_PAYLOAD_ROWS',
           (SELECT COUNT(*) FROM d WHERE SOURCE_SYSTEM_NAME IS DISTINCT FROM '__SOURCE_SYSTEM__' OR SOURCE_TABLE_NAME IS DISTINCT FROM '__SOURCE_NAME__' OR SOURCE_RECORD_ID IS NULL OR TRIM(SOURCE_RECORD_ID)='' OR SOURCE_RECORD_ID<>TRIM(SOURCE_RECORD_ID) OR NOT COALESCE(IS_OBJECT(METADATA_JSON),FALSE) OR NOT EXISTS (SELECT 1 FROM source_rows s WHERE s.SOURCE_RECORD_ID=d.SOURCE_RECORD_ID)), 0, 'DEFECT'
    UNION ALL
    SELECT 11, 'SOURCE_ROOT_OR_METADATA_COVERAGE_ERRORS',
           (SELECT COUNT(*) FROM source_rows s LEFT JOIN record_nodes r ON r.SOURCE_RECORD_ID=s.SOURCE_RECORD_ID WHERE COALESCE(r.ROOTS,0)<>1 OR COALESCE(r.METADATA_ROWS,0)<>1), 0, 'DEFECT'
    UNION ALL
    SELECT 12, 'UNEXPECTED_ELEMENT_TYPES',
           (SELECT COUNT(*) FROM d WHERE ELEMENT_TYPE IS NULL OR ELEMENT_TYPE NOT IN ('catalog','metadata','props')), 0, 'DEFECT'
    UNION ALL
    SELECT 13, 'NULL_OR_BLANK_FACT_REFERENCES',
           (SELECT COUNT(*) FROM f WHERE FK_SOURCE_ELEMENT_HASH IS NULL OR FK_TARGET_ELEMENT_HASH IS NULL OR SOURCE_OSCAL_UUID IS NULL OR TRIM(SOURCE_OSCAL_UUID)='' OR TARGET_OSCAL_UUID IS NULL OR TRIM(TARGET_OSCAL_UUID)=''), 0, 'DEFECT'
    UNION ALL
    SELECT 14, 'ORPHAN_SOURCE_FK',
           (SELECT COUNT(*) FROM f WHERE NOT EXISTS (SELECT 1 FROM d WHERE d.NODE_KEY=f.FK_SOURCE_ELEMENT_HASH)), 0, 'DEFECT'
    UNION ALL
    SELECT 15, 'ORPHAN_TARGET_FK',
           (SELECT COUNT(*) FROM f WHERE NOT EXISTS (SELECT 1 FROM d WHERE d.NODE_KEY=f.FK_TARGET_ELEMENT_HASH)), 0, 'DEFECT'
    UNION ALL
    SELECT 16, 'UUID_MISMATCH',
           (SELECT COUNT(*) FROM joined_edges WHERE SOURCE_OSCAL_UUID IS DISTINCT FROM PARENT_UUID OR TARGET_OSCAL_UUID IS DISTINCT FROM CHILD_UUID), 0, 'DEFECT'
    UNION ALL
    SELECT 17, 'CROSS_RECORD_OR_NAMESPACE_EDGES',
           (SELECT COUNT(*) FROM joined_edges WHERE PARENT_SYSTEM IS DISTINCT FROM CHILD_SYSTEM OR PARENT_TABLE IS DISTINCT FROM CHILD_TABLE OR PARENT_RECORD IS DISTINCT FROM CHILD_RECORD), 0, 'DEFECT'
    UNION ALL
    SELECT 18, 'INVALID_CONTAINS_OR_HIERARCHY_EDGES',
           (SELECT COUNT(*) FROM joined_edges WHERE DEPENDENCY_TYPE IS DISTINCT FROM 'CONTAINS' OR NOT COALESCE((SOURCE_TYPE='catalog' AND TARGET_TYPE='metadata') OR (SOURCE_TYPE='metadata' AND TARGET_TYPE='props'),FALSE) OR FK_SOURCE_ELEMENT_HASH=FK_TARGET_ELEMENT_HASH), 0, 'DEFECT'
    UNION ALL
    SELECT 19, 'WRONG_PARENT_COUNT',
           (SELECT COUNT(*) FROM parent_counts WHERE PARENTS<>CASE WHEN ELEMENT_TYPE='catalog' THEN 0 ELSE 1 END), 0, 'DEFECT'
    UNION ALL
    SELECT 20, 'MISSING_OR_DUPLICATE_TRACKING_PER_SOURCE',
           (SELECT COUNT(*) FROM source_valid s LEFT JOIN tracking_counts t ON t.SOURCE_RECORD_ID=s.SOURCE_RECORD_ID WHERE COALESCE(t.PROPERTY_ROWS,0)<>1), 0, 'DEFECT'
    UNION ALL
    SELECT 21, 'TRACKING_VALUE_OR_TYPE_MISMATCH',
           (SELECT COUNT(*) FROM tracking_comparison WHERE AS_VARCHAR(PROPERTY_VALUE) IS DISTINCT FROM EXPECTED_VALUE), 0, 'DEFECT'
),
results AS (
    SELECT CHECK_ORDER, QA_CHECK, OBSERVED_COUNT, EXPECTED_COUNT,
           CASE WHEN CHECK_KIND='INFO' THEN 'INFO'
                WHEN OBSERVED_COUNT=EXPECTED_COUNT THEN 'PASS'
                WHEN CHECK_KIND='INPUT' THEN 'BLOCKED'
                WHEN CHECK_KIND='BASELINE' THEN 'DRIFT'
                ELSE 'FAIL' END AS STATUS
    FROM checks
),
report AS (
    SELECT 0 AS CHECK_ORDER, 'OVERALL_CATALOG_POST_COMMIT_QA' AS QA_CHECK,
           SUM(CASE WHEN STATUS NOT IN ('PASS','INFO') THEN 1 ELSE 0 END) AS OBSERVED_COUNT,
           0 AS EXPECTED_COUNT,
           CASE WHEN SUM(CASE WHEN STATUS='BLOCKED' THEN 1 ELSE 0 END)>0 THEN 'BLOCKED'
                WHEN SUM(CASE WHEN STATUS='FAIL' THEN 1 ELSE 0 END)>0 THEN 'FAIL'
                WHEN SUM(CASE WHEN STATUS='DRIFT' THEN 1 ELSE 0 END)>0 THEN 'DRIFT'
                ELSE 'PASS' END AS STATUS
    FROM results
    UNION ALL SELECT CHECK_ORDER, QA_CHECK, OBSERVED_COUNT, EXPECTED_COUNT, STATUS FROM results
)
SELECT CURRENT_TIMESTAMP() AS QA_EXECUTED_AT,
       CHECK_ORDER, QA_CHECK, OBSERVED_COUNT, EXPECTED_COUNT, STATUS
FROM report
ORDER BY CHECK_ORDER;
'''
subs = {
    "__SOURCE_TABLE__": identifier(profile["RAW_TABLE"]),
    "__DIM_TABLE__": identifier(contract["TARGET_DIM"]),
    "__FACT_TABLE__": identifier(contract["TARGET_FACT"]),
    "__SOURCE_NAME__": literal(profile["SOURCE_TABLE_NAME"]),
    "__SOURCE_SYSTEM__": literal(profile["SOURCE_SYSTEM_NAME"]),
    "__TRACKING_FIELD__": literal(tracking_field),
}
for token, value in subs.items():
    sql = sql.replace(token, value)
if "__" in sql:
    raise RuntimeError("Unresolved placeholder in read-only Catalog check.")

print("SOURCE TWO CATALOG — INDEPENDENT READ-ONLY POST-COMMIT QA")
print("Size checks = INFO (current counts only, not historical baselines).")
print("Integrity/lineage checks: PASS / FAIL / BLOCKED.")
print("Overall PASS does not certify all 15 mapped values or full OSCAL conformance.")
# Snowpark .show() wraps SELECT SQL in a preview query. Keep the embedded
# SQL free of a trailing statement terminator; Snowflake rejects it there.
sql = sql.strip()
if sql.endswith(";"):
    sql = sql[:-1].rstrip()
if ";" in sql:
    raise RuntimeError("Unexpected internal statement delimiter in read-only QA SQL.")
session.sql(sql).show(n=25, max_width=130)
