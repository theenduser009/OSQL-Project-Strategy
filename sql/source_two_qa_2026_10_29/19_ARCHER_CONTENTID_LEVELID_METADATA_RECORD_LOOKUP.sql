-- 2026-10-29 | Source Two policy references | READ-ONLY discovery and resolution
-- Purpose: bridge OSCAL stored {ContentId,LevelId} to Archer Meta Content
-- and discover the correct level/module and physical policy record source.
-- This is NOT the ARCHER_META_VALUE select-list lookup.
-- Source references: Source Content ID in this script is a placeholder; keep
-- real private IDs and query results only in authorized Snowflake DEV.
-- Project branch examined: simplify-metadata-boundary @ fd351a087d28a7f1b4bed4246c559899a4d62040.
-- Historical 2026-09-10 owner screenshot: ARCHER_META_CONTENT has unique CONTENT_ID,
-- and 2026-10-01 candidate Matillion uses ARCHER_META_FIELD.LEVEL_ID.
-- Exact column names of physical level/module lookup are not yet verified.
-- Run statements ONE AT A TIME. No DML/DDL, no unverified JOIN keys.

-- 01. Discover actual metadata tables and their real columns. Look for
-- Meta Content (CONTENT_ID -> owning level), level/module metadata,
-- and whether any policy raw table is present under the current role.
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
       ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE
FROM RTX_RAW_DEV.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA='ES_ESC_GRC'
  AND (
       TABLE_NAME ILIKE 'ARCHER_META_CONTENT%'
       OR (TABLE_NAME ILIKE 'ARCHER%META%'
           AND (TABLE_NAME ILIKE '%LEVEL%'
                OR TABLE_NAME ILIKE '%MODULE%'
                OR TABLE_NAME ILIKE '%TABLE%'
                OR TABLE_NAME ILIKE '%FIELD%'))
       OR TABLE_NAME ILIKE 'ARCHER_CONTENT%POLIC%'
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 02. A real, previously observed metadata table, with verified CONTENT_ID.
-- Replace the literal before running. Inspect returned columns including
-- owning LEVEL_ID or equivalent; do not guess a name or module.
SELECT *
FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_CONTENT
WHERE CONTENT_ID::VARCHAR='REPLACE_REFERENCED_CONTENT_ID'
LIMIT 10;

-- 03. Join the stored OSCAL Component Definition 'policy-level' reference
-- to Archer Meta Content by target ContentId, exposing all metadata columns.
-- The Source root Content ID filters the OSCAL owner; it is NOT the referenced
-- Policy record ContentId. LevelId from the reference must also agree with
-- the owning level from Meta Content, after that column is identified.
WITH target_properties AS (
  SELECT d.SOURCE_TABLE_NAME, d.SOURCE_RECORD_ID AS OWNER_SOURCE_CONTENT_ID,
         d.METADATA_JSON:name::VARCHAR AS OSCAL_PROP_NAME,
         COALESCE(TRY_PARSE_JSON(d.METADATA_JSON:value::VARCHAR),
                  d.METADATA_JSON:value) AS REF_ARRAY
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_COMPONENT_ELEMENT d
  WHERE d.SOURCE_RECORD_ID::VARCHAR='REPLACE_OWNER_SOURCE_CONTENT_ID'
    AND d.ELEMENT_TYPE='props'
    AND d.METADATA_JSON:name::VARCHAR ILIKE '%policy%'
),
ref_items AS (
  SELECT t.SOURCE_TABLE_NAME, t.OWNER_SOURCE_CONTENT_ID,
         t.OSCAL_PROP_NAME,
         f.VALUE:ContentId::VARCHAR AS REFERENCED_CONTENT_ID,
         f.VALUE:LevelId::VARCHAR AS REFERENCED_LEVEL_ID,
         TYPEOF(f.VALUE) AS REFERENCE_ITEM_TYPE
  FROM target_properties t,
       LATERAL FLATTEN(
         INPUT=>IFF(IS_ARRAY(t.REF_ARRAY),t.REF_ARRAY,ARRAY_CONSTRUCT())
       ) f
)
SELECT r.SOURCE_TABLE_NAME,r.OWNER_SOURCE_CONTENT_ID,
       r.OSCAL_PROP_NAME, r.REFERENCED_CONTENT_ID,
       r.REFERENCED_LEVEL_ID,r.REFERENCE_ITEM_TYPE,
       IFF(mc.CONTENT_ID IS NULL,'NOT_FOUND_IN_META_CONTENT',
           'META_CONTENT_ID_FOUND_CHECK_LEVEL') AS MATCH_STATUS,
       mc.*
FROM ref_items r
LEFT JOIN RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_CONTENT mc
  ON mc.CONTENT_ID::VARCHAR=r.REFERENCED_CONTENT_ID
WHERE r.REFERENCED_CONTENT_ID IS NOT NULL
ORDER BY r.REFERENCED_CONTENT_ID
LIMIT 100;

-- 04. Find readable field names on the expected Policy Level 3 (LevelId 5).
-- This gives candidate name/title fields, NOT the field values of the record.
-- Meta Field FIELD_ID can be used for numeric FieldContents in actual RAW.
SELECT LEVEL_ID, FIELD_ID, SQL_FIELD_NAME, KEY_FIELD
FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_FIELD
WHERE LEVEL_ID=5
  AND (
       SQL_FIELD_NAME ILIKE '%NAME%'
       OR SQL_FIELD_NAME ILIKE '%TITLE%'
       OR SQL_FIELD_NAME ILIKE '%NUMBER%'
       OR SQL_FIELD_NAME ILIKE '%DESCRIPTION%'
  )
ORDER BY SQL_FIELD_NAME, FIELD_ID
LIMIT 100;

-- 05. Identify physical policy content tables with content id and curated JSON.
-- Cross-check candidates with the LevelId -> module mapping discovered in 01
-- and the owning level seen in 02/03 before selecting a business record table.
-- Actual name and location are NOT inferred from the words 'POLICY_LEVEL_3'.
WITH objects AS (
  SELECT TABLE_CATALOG, TABLE_SCHEMA,TABLE_NAME,
         COUNT_IF(UPPER(COLUMN_NAME)='CONTENT_ID') AS HAS_CONTENT_ID,
         COUNT_IF(UPPER(COLUMN_NAME)='CURATED_JSON') AS HAS_CURATED_JSON
  FROM RTX_RAW_DEV.INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA='ES_ESC_GRC'
    AND (TABLE_NAME ILIKE '%POLIC%'
         OR TABLE_NAME ILIKE '%POLICY%')
  GROUP BY 1,2,3
)
SELECT TABLE_CATALOG,TABLE_SCHEMA,TABLE_NAME
FROM objects
WHERE HAS_CONTENT_ID>0 AND HAS_CURATED_JSON>0
ORDER BY TABLE_NAME;
