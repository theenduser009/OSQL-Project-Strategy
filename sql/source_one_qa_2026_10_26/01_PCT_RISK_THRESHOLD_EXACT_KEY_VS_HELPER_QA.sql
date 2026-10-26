-- October 26, 2026 | READ ONLY | Snowflake DEV
-- Compare *exact* screenshot PCT field keys against distinct leading-underscore
-- Archer field keys. Similarity is NOT permission to alias or change mappings.
-- All four keys are APPROVED for Assessment Results results[].observations[];
-- distinct properties have distinct meanings until Archer owner says otherwise.
-- This is source population + stored observation presence only;
-- no complete value-equality or observed release/fingerprint claim.
WITH fields AS (
    SELECT column1::STRING AS ARCHER_FIELD_NAME,
           column2::STRING AS TARGET_PROPERTY_NAME
    FROM VALUES
      ('PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD',
       'pct-current-highest-device-risk-threshold'),
      ('PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD',
       'pct-current-average-device-risk-threshold'),
      ('_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD',
       'current-highest-device-risk-threshold'),
      ('_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD',
       'current-average-device-risk-threshold')
),
raw AS (
    SELECT CONTENT_ID::STRING AS CID, CURATED_JSON,
           COUNT(*) OVER (PARTITION BY CONTENT_ID::STRING) AS SOURCE_SNAPSHOTS
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW
),
source_rows AS (
    SELECT f.ARCHER_FIELD_NAME, f.TARGET_PROPERTY_NAME,
           r.CID, r.SOURCE_SNAPSHOTS,
           GET(r.CURATED_JSON, f.ARCHER_FIELD_NAME) AS ARCHER_VALUE
    FROM raw r CROSS JOIN fields f
),
source_classified AS (
    SELECT *,
        CASE
            WHEN ARCHER_VALUE IS NULL THEN 'SOURCE_KEY_ABSENT'
            WHEN IS_NULL_VALUE(ARCHER_VALUE) THEN 'EXPLICIT_JSON_NULL'
            WHEN TYPEOF(ARCHER_VALUE)='VARCHAR'
             AND LENGTH(TRIM(ARCHER_VALUE::STRING))=0 THEN 'SOURCE_EMPTY'
            WHEN IS_ARRAY(ARCHER_VALUE) AND ARRAY_SIZE(ARCHER_VALUE)=0
                THEN 'SOURCE_EMPTY'
            WHEN IS_OBJECT(ARCHER_VALUE)
             AND ARRAY_SIZE(OBJECT_KEYS(ARCHER_VALUE))=0
                THEN 'SOURCE_EMPTY'
            ELSE 'SOURCE_POPULATED'
        END AS SOURCE_STATE
    FROM source_rows
),
source_counts AS (
    SELECT ARCHER_FIELD_NAME, TARGET_PROPERTY_NAME, SOURCE_STATE,
           COUNT(*) AS RAW_ROWS,
           COUNT(DISTINCT CID) AS CONTENT_IDS,
           COUNT_IF(SOURCE_SNAPSHOTS > 1) AS AMBIGUOUS_SOURCE_ROWS,
           MIN(CID) AS EXAMPLE_CONTENT_ID
    FROM source_classified
    GROUP BY ARCHER_FIELD_NAME, TARGET_PROPERTY_NAME, SOURCE_STATE
),
target_counts AS (
    SELECT METADATA_JSON:"props"[0]:"name"::STRING AS TARGET_PROPERTY_NAME,
           COUNT(*) AS STORED_OBSERVATION_ROWS,
           COUNT(DISTINCT SOURCE_RECORD_ID) AS STORED_CONTENT_IDS,
           COUNT_IF(IS_NULL_VALUE(METADATA_JSON:"props"[0]:"value"))
               AS STORED_JSON_NULL_VALUES
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT
    WHERE ELEMENT_TYPE='observations'
      AND SOURCE_SYSTEM_NAME='ARCHER'
      AND SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND METADATA_JSON:"props"[0]:"name"::STRING IN (
          'pct-current-highest-device-risk-threshold',
          'pct-current-average-device-risk-threshold',
          'current-highest-device-risk-threshold',
          'current-average-device-risk-threshold'
      )
    GROUP BY METADATA_JSON:"props"[0]:"name"::STRING
)
SELECT s.ARCHER_FIELD_NAME,
       s.SOURCE_STATE, s.RAW_ROWS, s.CONTENT_IDS,
       COALESCE(s.AMBIGUOUS_SOURCE_ROWS,0) AS AMBIGUOUS_SOURCE_ROWS,
       s.TARGET_PROPERTY_NAME,
       COALESCE(t.STORED_OBSERVATION_ROWS,0) AS TARGET_OBSERVATION_ROWS,
       COALESCE(t.STORED_CONTENT_IDS,0) AS TARGET_CONTENT_IDS,
       COALESCE(t.STORED_JSON_NULL_VALUES,0) AS TARGET_JSON_NULL_ROWS,
       s.EXAMPLE_CONTENT_ID
FROM source_counts s
LEFT JOIN target_counts t
    ON t.TARGET_PROPERTY_NAME = s.TARGET_PROPERTY_NAME
ORDER BY s.ARCHER_FIELD_NAME, s.SOURCE_STATE;
