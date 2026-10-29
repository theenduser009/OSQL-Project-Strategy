-- SYSTEM SECURITY PLAN (SOURCE ONE) | 2026-10-29 | READ ONLY | NO ARCHER RAW TABLES
-- Output: CONTENT_ID, SOURCE_TABLE_NAME, OSCAL_ELEMENT_PATH,
--         OSCAL_ELEMENT, ARCHER_FIELD_NAME, FIELD_VALUE
-- Field names are reconstructed from approved mapping identity or unique native
-- mappings, not automatically read from a universal Archer column in DIM.
-- Sample only; test in DEV and verify deployed mapping/registry before QA PASS.

-- 1: AUTHORIZATION_PACKAGE_NAME -> system-security-plan.system-characteristics.system-name (two approved native destinations)
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID,d.SOURCE_TABLE_NAME,
       'system-security-plan.system-characteristics.system-name' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'AUTHORIZATION_PACKAGE_NAME' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:"system-name" AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT d
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
  AND d.ELEMENT_TYPE='system-characteristics'
  AND d.METADATA_JSON:"system-name" IS NOT NULL
ORDER BY CONTENT_ID LIMIT 25;

-- 2: AUTHORIZATION_PACKAGE_NAME -> system-security-plan.metadata.title (two approved native destinations)
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID,d.SOURCE_TABLE_NAME,
       'system-security-plan.metadata.title' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'AUTHORIZATION_PACKAGE_NAME' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:"title" AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT d
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
  AND d.ELEMENT_TYPE='metadata'
  AND d.METADATA_JSON:"title" IS NOT NULL
ORDER BY CONTENT_ID LIMIT 25;
