-- COMPONENT DEFINITION | 2026-10-29 | READ ONLY | NO ARCHER RAW TABLES
-- Output: CONTENT_ID, SOURCE_TABLE_NAME, OSCAL_ELEMENT_PATH,
--         OSCAL_ELEMENT, ARCHER_FIELD_NAME, FIELD_VALUE
-- Field names are reconstructed from approved mapping identity or unique native
-- mappings, not automatically read from a universal Archer column in DIM.
-- Sample only; test in DEV and verify deployed mapping/registry before QA PASS.

-- 1: POLICY_LEVEL_3; same policy-level name is NOT sufficient.
-- Verify exact field+value derived DIM hash, distinct for every Archer field.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID, d.SOURCE_TABLE_NAME,
       'component-definition.components[].props[policy-level].value' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'POLICY_LEVEL_3' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:value AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_COMPONENT_ELEMENT d
WHERE d.ELEMENT_TYPE='props'
  AND d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW'
  AND d.METADATA_JSON:name::VARCHAR='policy-level'
  AND d.PK_DIM_OSCAL_COMPONENT_ELEMENT_HASH = MD5_BINARY(
    'v1_registry_path_instance|ARCHER|'||d.SOURCE_TABLE_NAME||'|'||
    d.SOURCE_RECORD_ID||'|COMPONENT_DEFINITION|'||
    'component-definition.components[].props[]|'||
    'POLICY_LEVEL_3:'||MD5('source-field-value-v1|POLICY_LEVEL_3|'||
      d.METADATA_JSON:value::VARCHAR)
  )
ORDER BY CONTENT_ID LIMIT 25;

-- 2: POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS; same policy-level name is NOT sufficient.
-- Verify exact field+value derived DIM hash, distinct for every Archer field.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID, d.SOURCE_TABLE_NAME,
       'component-definition.components[].props[policy-level].value' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:value AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_COMPONENT_ELEMENT d
WHERE d.ELEMENT_TYPE='props'
  AND d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW'
  AND d.METADATA_JSON:name::VARCHAR='policy-level'
  AND d.PK_DIM_OSCAL_COMPONENT_ELEMENT_HASH = MD5_BINARY(
    'v1_registry_path_instance|ARCHER|'||d.SOURCE_TABLE_NAME||'|'||
    d.SOURCE_RECORD_ID||'|COMPONENT_DEFINITION|'||
    'component-definition.components[].props[]|'||
    'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS:'||MD5('source-field-value-v1|POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS|'||
      d.METADATA_JSON:value::VARCHAR)
  )
ORDER BY CONTENT_ID LIMIT 25;
