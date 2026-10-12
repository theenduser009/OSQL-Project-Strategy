-- OSCAL SSP: Archer field-lineage lookup (READ ONLY)
-- Published: 2026-10-12
--
-- This query checks the proposed convention:
--   separate SSP DIM props node: {"name":"source-field","value":"<ARCHER_FIELD_NAME>"}
-- The presence of these rows in live Snowflake has NOT been verified.
-- Historical mapper code alone does not prove they were persisted.
--
-- Replace the table identifier below with your authorized DEV SSP DIM table.
-- Do not publish customer table names, source records or returned values.
SET SSP_DIM_TABLE = 'YOUR_DATABASE.YOUR_SCHEMA.DIM_OSCAL_SSP_ELEMENT';

-- Query 1: Find the Archer field-name lineage property.
SELECT
    p.SOURCE_RECORD_ID,
    p.METADATA_JSON:"name"::STRING AS PROP_NAME,
    p.METADATA_JSON:"value"::STRING AS ARCHER_FIELD_NAME
FROM IDENTIFIER($SSP_DIM_TABLE) AS p
WHERE LOWER(p.ELEMENT_TYPE) = 'props'
  AND p.METADATA_JSON:"name"::STRING = 'source-field'
  AND p.METADATA_JSON:"value"::STRING =
      'RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY'
ORDER BY p.SOURCE_RECORD_ID
LIMIT 20;

-- Query 2: Show that source-record's lineage property beside its SSP value.
-- Joining by SOURCE_RECORD_ID establishes record association, not which of
-- several Archer fields mapping to one OSCAL target supplied the winning value.
SELECT
    p.SOURCE_RECORD_ID,
    p.METADATA_JSON:"value"::STRING AS ARCHER_FIELD_NAME,
    s.METADATA_JSON:"security-objective-confidentiality"::STRING
        AS OSCAL_VALUE
FROM IDENTIFIER($SSP_DIM_TABLE) AS p
JOIN IDENTIFIER($SSP_DIM_TABLE) AS s
    ON p.SOURCE_RECORD_ID = s.SOURCE_RECORD_ID
WHERE LOWER(p.ELEMENT_TYPE) = 'props'
  AND p.METADATA_JSON:"name"::STRING = 'source-field'
  AND p.METADATA_JSON:"value"::STRING =
      'RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY'
  AND LOWER(s.ELEMENT_TYPE) = 'security-impact-level'
ORDER BY p.SOURCE_RECORD_ID
LIMIT 20;

-- If Query 1 returns no rows, do not conclude lineage is absent everywhere.
-- Check your current deployed mapper/version and actual SSP property payloads.
