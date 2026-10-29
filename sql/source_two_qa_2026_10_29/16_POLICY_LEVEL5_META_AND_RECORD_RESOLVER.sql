-- Source Two policy reference resolver diagnostic, 2026-10-29.
-- Snowflake DEV, SELECT only; run ONE query at a time.
-- ContentId/LevelId is a referenced Archer RECORD, not a select-list
-- ValuesListId for ARCHER_META_VALUE. Owner's Policy Level 2 sample shows
-- POLICY_LEVEL_3_REFERENCE with LevelId=5.
-- Repo code verified at simplify-metadata-boundary 9398f6de6b78b5f0c2c183bd01d960f0f37ab827.
-- Meta table/Policy Level 3 record table must be confirmed in live DB before
-- assuming a complete identifier->name resolution. No database execution here.

-- QUERY 1: discover accessible physical levels/fields/relationship and policy
-- metadata tables. Historic guide says Archer_Meta_Levels/Fields/Field_Relationships,
-- but those descriptive names are NOT proof of exact DEV table spelling.
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM RTX_RAW_DEV.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA='ES_ESC_GRC'
  AND (
      (TABLE_NAME ILIKE 'ARCHER%META%'
       AND (TABLE_NAME ILIKE '%LEVEL%' OR TABLE_NAME ILIKE '%FIELD%'
            OR TABLE_NAME ILIKE '%RELATIONSHIP%'))
      OR REGEXP_LIKE(UPPER(TABLE_NAME),
           '^ARCHER_CONTENT_POLICIES_(POLICY_)?LEVEL_[123]_RAW$')
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- QUERY 2: physically documented Archer field metadata, LevelId=5.
-- This is field ownership metadata, NOT the referenced record's data/name.
SELECT LEVEL_ID, FIELD_ID, SQL_FIELD_NAME, KEY_FIELD
FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_FIELD
WHERE LEVEL_ID=5
ORDER BY SQL_FIELD_NAME, FIELD_ID
LIMIT 200;

-- QUERY 3: parse policy ContentId/LevelId from persisted OSCAL only.
-- Replace REPLACE_SOURCE_CONTENT_ID with the root Source ID from your result.
-- For Catalog groups, root SOURCE_RECORD_ID != a Topic/Section child ID.
WITH field_values AS (
  SELECT 'COMPONENT_DEFINITION' AS MODEL, d.SOURCE_TABLE_NAME,
         d.SOURCE_RECORD_ID AS ROOT_SOURCE_CONTENT_ID,
         d.ELEMENT_TYPE, d.METADATA_JSON:name::VARCHAR AS PROPERTY_NAME,
         d.METADATA_JSON:value AS STORED_VALUE
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_COMPONENT_ELEMENT d
  WHERE d.SOURCE_RECORD_ID='REPLACE_SOURCE_CONTENT_ID'
    AND d.ELEMENT_TYPE='props'
    AND d.METADATA_JSON:name::VARCHAR ILIKE '%polic%'
  UNION ALL
  SELECT 'CATALOG', d.SOURCE_TABLE_NAME, d.SOURCE_RECORD_ID,
         d.ELEMENT_TYPE, p.VALUE:name::VARCHAR, p.VALUE:value
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT d,
       LATERAL FLATTEN(INPUT=>d.METADATA_JSON:props) p
  WHERE d.SOURCE_RECORD_ID='REPLACE_SOURCE_CONTENT_ID'
    AND p.VALUE:name::VARCHAR ILIKE '%polic%'
), parsed AS (
  SELECT *, COALESCE(TRY_PARSE_JSON(STORED_VALUE::VARCHAR),
                     STORED_VALUE) AS REF_ARRAY
  FROM field_values
)
SELECT MODEL, SOURCE_TABLE_NAME, ROOT_SOURCE_CONTENT_ID, ELEMENT_TYPE,
       PROPERTY_NAME, TYPEOF(REF_ARRAY) AS PARSED_TYPE,
       r.VALUE:ContentId::VARCHAR AS REFERENCED_CONTENT_ID,
       r.VALUE:LevelId::VARCHAR AS REFERENCED_LEVEL_ID,
       IFF(r.VALUE:ContentId IS NOT NULL AND r.VALUE:LevelId IS NOT NULL,
           'IDENTIFIERS_EXTRACTED_NOT_LOOKED_UP',
           'SCALAR_OR_UNRECOGNIZED_REFERENCE') AS REFERENCE_STATUS
FROM parsed p,
     LATERAL FLATTEN(INPUT=>IFF(IS_ARRAY(p.REF_ARRAY),
                                p.REF_ARRAY, ARRAY_CONSTRUCT()),
                     OUTER=>TRUE) r
ORDER BY MODEL, PROPERTY_NAME, REFERENCED_CONTENT_ID
LIMIT 100;

-- QUERY 4: discover ACTUAL policy record tables with CONTENT_ID/CURATED_JSON
-- and generate a ready-to-copy SELECT. No imaginary policy table is used.
-- After Query 1 identifies the actual level metadata table, confirm LevelId=5
-- is Policy Level 3; then replace the generated referenced ID from Query 3.
WITH table_inventory AS (
  SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
         COUNT_IF(UPPER(COLUMN_NAME)='CONTENT_ID') AS HAS_CONTENT_ID,
         COUNT_IF(UPPER(COLUMN_NAME)='CURATED_JSON') AS HAS_CURATED_JSON
  FROM RTX_RAW_DEV.INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA='ES_ESC_GRC'
    AND REGEXP_LIKE(UPPER(TABLE_NAME),
        '^ARCHER_CONTENT_POLICIES_(POLICY_)?LEVEL_[123]_RAW$')
  GROUP BY TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME
)
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
       'SELECT CONTENT_ID::VARCHAR AS POLICY_CONTENT_ID, ' ||
       '(IFF(TYPEOF(CURATED_JSON)=''VARCHAR'', ' ||
       'TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON)),CURATED_JSON)):' ||
       'POLICY_LEVEL_3_NAME AS POLICY_LEVEL_3_NAME, ' ||
       'IFF(TYPEOF(CURATED_JSON)=''VARCHAR'', ' ||
       'TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON)),CURATED_JSON) AS POLICY_JSON ' ||
       'FROM "' || TABLE_CATALOG || '"."' || TABLE_SCHEMA || '"."' || TABLE_NAME || '" ' ||
       'WHERE CONTENT_ID::VARCHAR=''REPLACE_REFERENCED_CONTENT_ID'';' AS SQL_TO_RUN
FROM table_inventory
WHERE HAS_CONTENT_ID > 0 AND HAS_CURATED_JSON > 0
ORDER BY TABLE_NAME
LIMIT 30;
