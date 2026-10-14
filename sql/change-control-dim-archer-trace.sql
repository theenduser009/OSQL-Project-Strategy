-- Read-only Change Control trace: persisted OSCAL DIM -> FACT parent -> Archer source.
-- Copy this complete file into a Snowflake SQL worksheet and run it.
-- No notebook state, SET variables, DDL, or DML required.
-- CHANGE_CONTROL maps to the named business property 'change-control'.
-- The Archer field and OSCAL path below are established by the approved mapping.
-- Multiple retained RAW versions of one Content ID can repeat source comparisons;
-- this query is an inspection, not latest-snapshot parity QA.

SELECT
  p.SOURCE_RECORD_ID,
  p.SOURCE_TABLE_NAME AS ARCHER_TABLE,
  'CHANGE_CONTROL' AS ARCHER_FIELD,
  'system-security-plan.system-characteristics.props[]' AS OSCAL_PATH,
  p.METADATA_JSON:"name"::STRING AS OSCAL_PROPERTY,
  p.METADATA_JSON:"value" AS OSCAL_VALUE,
  s.CURATED_JSON:"CHANGE_CONTROL" AS ARCHER_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT p
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY f
  ON f.FK_TARGET_ELEMENT_HASH = p.PK_OSCAL_SSP_ELEMENT_HASH
 AND f.DEPENDENCY_TYPE = 'CONTAINS'
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT parent
  ON parent.PK_OSCAL_SSP_ELEMENT_HASH = f.FK_SOURCE_ELEMENT_HASH
 AND parent.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID
LEFT JOIN RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW s
  ON s.CONTENT_ID::STRING = p.SOURCE_RECORD_ID
WHERE p.ELEMENT_TYPE = 'props'
  AND p.METADATA_JSON:"name"::STRING = 'change-control'
  AND parent.ELEMENT_TYPE = 'system-characteristics'
  AND p.SOURCE_SYSTEM_NAME = 'ARCHER'
  AND p.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
ORDER BY p.SOURCE_RECORD_ID
LIMIT 20;
