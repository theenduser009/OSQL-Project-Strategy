-- SSP property source-to-target inspection (read only).
-- This worksheet compares an approved source field with the corresponding
-- persisted SSP system-characteristics property for the same source record.
-- Replace the seven placeholder SET values below before running in Snowflake.
-- The approved mapping contract determines the source field and property name.
-- This is not a full snapshot-aware parity certification; see NOTES below.

SET SOURCE_TABLE = '<RAW_DATABASE>.<SOURCE_SCHEMA>.<AUTHORIZATION_PACKAGE_SOURCE_TABLE>';
SET SSP_DIM_TABLE = '<CURATED_DATABASE>.<CURATED_SCHEMA>.<SSP_DIM_TABLE>';
SET SSP_FACT_TABLE = '<CURATED_DATABASE>.<CURATED_SCHEMA>.<SSP_FACT_TABLE>';
SET SOURCE_SYSTEM = '<SOURCE_SYSTEM_NAME>';
SET SOURCE_TABLE_NAME = '<SOURCE_TABLE_BASENAME>';
SET ARCHER_FIELD = '<SOURCE_FIELD_NAME>';
SET OSCAL_PROP = '<APPROVED_PROPERTY_NAME>';

WITH target AS (
    SELECT
        sc.SOURCE_RECORD_ID,
        p.METADATA_JSON:"name"::STRING AS PROP_NAME,
        p.METADATA_JSON:"value" AS OSCAL_VALUE
    FROM IDENTIFIER($SSP_DIM_TABLE) sc
    JOIN IDENTIFIER($SSP_FACT_TABLE) f
      ON f.FK_SOURCE_ELEMENT_HASH = sc.PK_OSCAL_SSP_ELEMENT_HASH
     AND f.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN IDENTIFIER($SSP_DIM_TABLE) p
      ON p.PK_OSCAL_SSP_ELEMENT_HASH = f.FK_TARGET_ELEMENT_HASH
    WHERE sc.ELEMENT_TYPE = 'system-characteristics'
      AND p.ELEMENT_TYPE = 'props'
      AND sc.SOURCE_SYSTEM_NAME = $SOURCE_SYSTEM
      AND sc.SOURCE_TABLE_NAME = $SOURCE_TABLE_NAME
      AND p.SOURCE_SYSTEM_NAME = sc.SOURCE_SYSTEM_NAME
      AND p.SOURCE_TABLE_NAME = sc.SOURCE_TABLE_NAME
      AND p.SOURCE_RECORD_ID = sc.SOURCE_RECORD_ID
      AND p.METADATA_JSON:"name"::STRING = $OSCAL_PROP
)
SELECT
    s.CONTENT_ID::STRING AS SOURCE_RECORD_ID,
    $ARCHER_FIELD AS ARCHER_COLUMN_NAME,
    GET(s.CURATED_JSON, $ARCHER_FIELD) AS ARCHER_VALUE,
    t.PROP_NAME AS OSCAL_PROPERTY_NAME,
    t.OSCAL_VALUE,
    CASE WHEN t.SOURCE_RECORD_ID IS NULL
         THEN 'PERSISTED_PROP_NOT_FOUND'
         ELSE 'PERSISTED_PROP_FOUND' END AS LOOKUP_STATUS
FROM IDENTIFIER($SOURCE_TABLE) s
LEFT JOIN target t
  ON t.SOURCE_RECORD_ID = s.CONTENT_ID::STRING
WHERE GET(s.CURATED_JSON, $ARCHER_FIELD) IS NOT NULL
  AND NOT IS_NULL_VALUE(GET(s.CURATED_JSON, $ARCHER_FIELD))
ORDER BY s.CONTENT_ID::STRING
LIMIT 20;

-- NOTES
-- 1. A source value that is JSON null is intentionally excluded from this
--    populated-value inspection. Query null-only mappings separately.
-- 2. If the source table has multiple versions per CONTENT_ID, use the
--    approved latest-record selection before asserting source-value parity.
-- 3. If one source value maps to multiple property values, review all rows.
-- 4. Property name is the mapped OSCAL name; Archer FieldId requires separate
--    Archer metadata with LevelId context.
