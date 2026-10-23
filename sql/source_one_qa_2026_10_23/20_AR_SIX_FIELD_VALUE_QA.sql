-- Source One Assessment Results: six fields from "Fields are not found".
-- 2026-10-23 | READ ONLY | Snowflake DEV. Metadata from exact Source One CSV.
-- Two thresholds target results[].observations[] (embedded props[0]).
-- Four other fields target results[].props[] (standalone DIM children).
-- This query verifies root -> results -> child FACT ownership and scalar values.
-- For multi-reference lists or non-ISO dates, it reports REVIEW, never PASS.
-- Historical AR30 COMMIT is not proof of newer AR32/current fields.
WITH mapping_fields AS (
    SELECT column1::STRING AS FIELD_NAME,
           column2::STRING AS TARGET_KIND,
           column3::STRING AS TRANSFORM_ID,
           column4::STRING AS PRESERVE_EXPLICIT_NULL
    FROM VALUES
      ('FINDINGS', 'props', 'direct', 'Y'),
      ('RISK_ACCEPTANCE_RBDS', 'props', 'reference-ids', 'N'),
      ('PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD', 'observations', 'scalar-score', 'Y'),
      ('PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD', 'observations', 'scalar-score', 'Y'),
      ('RISK_ASSESSMENT_REPORT', 'props', 'json-text', 'N'),
      ('DUE_DATE', 'props', 'date', 'N')
),
raw AS (
    SELECT CONTENT_ID::STRING AS CONTENT_ID,
           CURATED_JSON,
           COUNT(*) OVER (PARTITION BY CONTENT_ID::STRING) AS SNAPSHOT_COUNT
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW
),
sources AS (
    SELECT r.CONTENT_ID, r.SNAPSHOT_COUNT,
           m.FIELD_NAME, m.TARGET_KIND, m.TRANSFORM_ID, m.PRESERVE_EXPLICIT_NULL,
           GET(r.CURATED_JSON, m.FIELD_NAME) AS SOURCE_VALUE,
           LOWER(REGEXP_REPLACE(m.FIELD_NAME, '[^A-Za-z0-9]+', '-')) AS PROPERTY_NAME
    FROM raw r CROSS JOIN mapping_fields m
),
prepared AS (
    SELECT *,
           CASE
             WHEN SOURCE_VALUE IS NULL THEN 'SOURCE_KEY_ABSENT'
             WHEN IS_NULL_VALUE(SOURCE_VALUE) THEN 'EXPLICIT_JSON_NULL'
             WHEN TYPEOF(SOURCE_VALUE) = 'VARCHAR'
                  AND LENGTH(TRIM(SOURCE_VALUE::STRING)) = 0 THEN 'SOURCE_EMPTY'
             WHEN IS_ARRAY(SOURCE_VALUE) AND ARRAY_SIZE(SOURCE_VALUE)=0
                  THEN 'SOURCE_EMPTY'
             WHEN IS_OBJECT(SOURCE_VALUE)
                  AND ARRAY_SIZE(OBJECT_KEYS(SOURCE_VALUE))=0
                  THEN 'SOURCE_EMPTY'
             ELSE 'SOURCE_POPULATED'
           END AS SOURCE_STATE,
           CASE
             WHEN TRANSFORM_ID = 'json-text' THEN 'JSON_TEXT'
             WHEN TRANSFORM_ID = 'date' AND
                REGEXP_LIKE(SOURCE_VALUE::STRING,
                            '[0-9]{4}-[0-9]{2}-[0-9]{2}([Tt ].*)?')
                AND TRY_TO_DATE(LEFT(SOURCE_VALUE::STRING,10)) IS NOT NULL
                    THEN 'SCALAR'
             WHEN TRANSFORM_ID = 'reference-ids' AND
                (NOT IS_ARRAY(SOURCE_VALUE) OR ARRAY_SIZE(SOURCE_VALUE)=1)
                    THEN 'SCALAR'
             WHEN TRANSFORM_ID IN ('direct','scalar-score') AND
                TYPEOF(SOURCE_VALUE) IN ('VARCHAR','INTEGER','DECIMAL',
                                          'DOUBLE','BOOLEAN')
                    THEN 'SCALAR'
             WHEN TRANSFORM_ID = 'scalar-score' AND
                IS_ARRAY(SOURCE_VALUE:"ResolvedValues")
                AND ARRAY_SIZE(SOURCE_VALUE:"ResolvedValues")=1
                AND SOURCE_VALUE:"ResolvedValues"[0]:"LookupStatus"::STRING='MATCHED'
                    THEN 'SCALAR'
             ELSE 'REVIEW_SHAPE'
           END AS VALUE_SHAPE,
           CASE
             WHEN TRANSFORM_ID = 'date'
                 THEN LEFT(SOURCE_VALUE::STRING,10)
             WHEN TRANSFORM_ID = 'reference-ids' THEN
                 COALESCE(
                     SOURCE_VALUE:"ContentId"::STRING,
                     SOURCE_VALUE[0]:"ContentId"::STRING,
                     IFF(IS_ARRAY(SOURCE_VALUE) AND ARRAY_SIZE(SOURCE_VALUE)=1,
                         SOURCE_VALUE[0]::STRING, NULL),
                     IFF(NOT IS_ARRAY(SOURCE_VALUE)
                             AND NOT IS_OBJECT(SOURCE_VALUE),
                         SOURCE_VALUE::STRING, NULL)
                 )
             WHEN TRANSFORM_ID = 'scalar-score'
                  AND IS_ARRAY(SOURCE_VALUE:"ResolvedValues")
                  AND ARRAY_SIZE(SOURCE_VALUE:"ResolvedValues")=1
                 THEN SOURCE_VALUE:"ResolvedValues"[0]:"ValueName"::STRING
             WHEN TRANSFORM_ID IN ('direct','scalar-score')
                 THEN SOURCE_VALUE::STRING
             ELSE NULL
           END AS EXPECTED_SCALAR
    FROM sources
),
owned_targets AS (
    SELECT child.SOURCE_RECORD_ID AS CONTENT_ID,
           child.ELEMENT_TYPE AS TARGET_KIND,
           IFF(child.ELEMENT_TYPE='observations',
               child.METADATA_JSON:"props"[0]:"name"::STRING,
               child.METADATA_JSON:"name"::STRING) AS PROPERTY_NAME,
           IFF(child.ELEMENT_TYPE='observations',
               child.METADATA_JSON:"props"[0]:"value",
               child.METADATA_JSON:"value") AS TARGET_VALUE
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT root
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_ASSESSMENT_RESULTS_DEPENDENCY root_edge
      ON root_edge.FK_SOURCE_ELEMENT_HASH =
            root.PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH
     AND root_edge.DEPENDENCY_TYPE='CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT result
      ON result.PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH =
            root_edge.FK_TARGET_ELEMENT_HASH
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_ASSESSMENT_RESULTS_DEPENDENCY child_edge
      ON child_edge.FK_SOURCE_ELEMENT_HASH =
            result.PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH
     AND child_edge.DEPENDENCY_TYPE='CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT child
      ON child.PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH =
            child_edge.FK_TARGET_ELEMENT_HASH
    WHERE root.ELEMENT_TYPE='assessment-results'
      AND result.ELEMENT_TYPE='results'
      AND child.ELEMENT_TYPE IN ('props','observations')
      AND root.SOURCE_SYSTEM_NAME='ARCHER'
      AND root.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND result.SOURCE_SYSTEM_NAME=root.SOURCE_SYSTEM_NAME
      AND child.SOURCE_SYSTEM_NAME=root.SOURCE_SYSTEM_NAME
      AND result.SOURCE_TABLE_NAME=root.SOURCE_TABLE_NAME
      AND child.SOURCE_TABLE_NAME=root.SOURCE_TABLE_NAME
      AND result.SOURCE_RECORD_ID=root.SOURCE_RECORD_ID
      AND child.SOURCE_RECORD_ID=root.SOURCE_RECORD_ID
),
comparisons AS (
    SELECT s.CONTENT_ID, s.SNAPSHOT_COUNT, s.FIELD_NAME, s.TARGET_KIND,
           s.TRANSFORM_ID, s.PRESERVE_EXPLICIT_NULL, s.SOURCE_STATE,
           s.VALUE_SHAPE, s.SOURCE_VALUE, s.EXPECTED_SCALAR,
           COUNT(t.PROPERTY_NAME) AS TARGET_ELEMENTS,
           COALESCE(COUNT_IF(IS_NULL_VALUE(t.TARGET_VALUE)),0) AS TARGET_EXPLICIT_NULLS,
           COALESCE(COUNT_IF(
                CASE
                  WHEN s.TRANSFORM_ID='json-text'
                    THEN TRY_PARSE_JSON(t.TARGET_VALUE::STRING)=s.SOURCE_VALUE
                  WHEN s.VALUE_SHAPE='SCALAR'
                    THEN t.TARGET_VALUE::STRING=s.EXPECTED_SCALAR
                  ELSE FALSE
                END),0) AS MATCHED_ELEMENTS
    FROM prepared s
    LEFT JOIN owned_targets t
      ON t.CONTENT_ID=s.CONTENT_ID
     AND t.TARGET_KIND=s.TARGET_KIND
     AND t.PROPERTY_NAME=s.PROPERTY_NAME
    GROUP BY ALL
),
qa AS (
    SELECT CONTENT_ID, FIELD_NAME, TARGET_KIND, TRANSFORM_ID,
           SNAPSHOT_COUNT, SOURCE_STATE, VALUE_SHAPE,
           TARGET_ELEMENTS, TARGET_EXPLICIT_NULLS, MATCHED_ELEMENTS,
           CASE
             WHEN SNAPSHOT_COUNT>1 THEN 'SOURCE_SNAPSHOT_AMBIGUOUS'
             WHEN SOURCE_STATE='SOURCE_KEY_ABSENT' AND TARGET_ELEMENTS>0
                    THEN 'UNEXPECTED_TARGET_ABSENT_SOURCE'
             WHEN SOURCE_STATE='SOURCE_KEY_ABSENT' THEN 'SOURCE_KEY_ABSENT'
             WHEN SOURCE_STATE='SOURCE_EMPTY' AND TARGET_ELEMENTS>0
                    THEN 'TARGET_PRESENT_EMPTY_SOURCE_REVIEW'
             WHEN SOURCE_STATE='SOURCE_EMPTY' THEN 'SOURCE_EMPTY'
             WHEN SOURCE_STATE='EXPLICIT_JSON_NULL'
               AND PRESERVE_EXPLICIT_NULL='Y'
               AND TARGET_ELEMENTS=1 AND TARGET_EXPLICIT_NULLS=1
                    THEN 'EXPLICIT_NULL_PRESERVED'
             WHEN SOURCE_STATE='EXPLICIT_JSON_NULL'
               AND PRESERVE_EXPLICIT_NULL='Y'
               AND TARGET_ELEMENTS=0
                    THEN 'PRESERVED_NULL_TARGET_MISSING'
             WHEN SOURCE_STATE='EXPLICIT_JSON_NULL' AND TARGET_ELEMENTS=0
                    THEN 'SOURCE_NULL_OMITTED'
             WHEN SOURCE_STATE='EXPLICIT_JSON_NULL'
                    THEN 'NULL_SOURCE_TARGET_REVIEW'
             WHEN TARGET_ELEMENTS=0 THEN 'POPULATED_SOURCE_TARGET_MISSING'
             WHEN TARGET_ELEMENTS>1 THEN 'MULTIPLE_TARGET_VALUES_REVIEW'
             WHEN VALUE_SHAPE='REVIEW_SHAPE'
                    THEN 'TARGET_PRESENT_SOURCE_SHAPE_REVIEW'
             WHEN MATCHED_ELEMENTS=1 THEN 'VALUE_MATCH'
             ELSE 'VALUE_MISMATCH'
           END AS QA_STATUS
    FROM comparisons
)
SELECT FIELD_NAME AS ARCHER_FIELD_NAME, TARGET_KIND, TRANSFORM_ID, QA_STATUS,
       COUNT(*) AS SOURCE_ROWS,
       COUNT(DISTINCT CONTENT_ID) AS DISTINCT_CONTENT_IDS,
       SUM(TARGET_ELEMENTS) AS TARGET_ELEMENTS,
       SUM(MATCHED_ELEMENTS) AS MATCHED_ELEMENTS,
       MIN(CONTENT_ID) AS EXAMPLE_CONTENT_ID
FROM qa
GROUP BY FIELD_NAME, TARGET_KIND, TRANSFORM_ID, QA_STATUS
ORDER BY ARCHER_FIELD_NAME, QA_STATUS;
