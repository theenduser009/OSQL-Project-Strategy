-- 2026-10-29. Source Two: null Archer field vs populated OSCAL target diagnostic.
-- READ-ONLY. Run separately. NO Archer RAW access. Not executed in Snowflake by publisher.
-- Sample IDs were visible in the owner's screenshot; replace them for other records.
-- This is a TARGET PRESENCE inspection, not a proof of field provenance.
-- A property-name match by itself must never be counted as a source-field QA PASS.

-- 01. Does Component Definition physically contain a policy-related prop
-- for these exact Source-level Content IDs, ignoring the strict field-hash filter?
SELECT
  'COMPONENT_DEFINITION' AS OSCAL_MODEL,
  d.SOURCE_TABLE_NAME,
  d.SOURCE_RECORD_ID AS CONTENT_ID,
  d.ELEMENT_TYPE,
  d.METADATA_JSON:name::VARCHAR AS OSCAL_PROPERTY_NAME,
  d.METADATA_JSON:value AS OSCAL_VALUE,
  TO_VARCHAR(d.PK_DIM_OSCAL_COMPONENT_ELEMENT_HASH, 'HEX') AS STORED_DIM_HASH
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_COMPONENT_ELEMENT d
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW'
  AND d.SOURCE_RECORD_ID IN ('185810','185837','207242')
  AND d.ELEMENT_TYPE='props'
  AND d.METADATA_JSON:name::VARCHAR ILIKE '%policy%'
ORDER BY CONTENT_ID, OSCAL_PROPERTY_NAME;

-- 02. Is that value present under Catalog instead of Component Definition?
-- Checks separately stored props AND props embedded inside metadata/group nodes.
-- Catalog group descendants may use a root SOURCE_RECORD_ID and store their own
-- Archer child Content ID as an embedded 'archer-content-id' property.
SELECT
  'CATALOG' AS OSCAL_MODEL,
  d.SOURCE_TABLE_NAME,
  d.SOURCE_RECORD_ID AS CONTENT_ID,
  d.ELEMENT_TYPE,
  COALESCE(d.METADATA_JSON:name::VARCHAR,
           nested.VALUE:name::VARCHAR) AS OSCAL_PROPERTY_NAME,
  COALESCE(d.METADATA_JSON:value,
           nested.VALUE:value) AS OSCAL_VALUE,
  TO_VARCHAR(d.PK_DIM_OSCAL_CATALOG_ELEMENT_HASH, 'HEX') AS STORED_DIM_HASH
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT d,
     LATERAL FLATTEN(INPUT=>d.METADATA_JSON:props, OUTER=>TRUE) nested
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW'
  AND d.SOURCE_RECORD_ID IN ('185810','185837','207242')
  AND (d.METADATA_JSON:name::VARCHAR ILIKE '%policy%'
       OR nested.VALUE:name::VARCHAR ILIKE '%policy%')
ORDER BY CONTENT_ID, OSCAL_PROPERTY_NAME;
