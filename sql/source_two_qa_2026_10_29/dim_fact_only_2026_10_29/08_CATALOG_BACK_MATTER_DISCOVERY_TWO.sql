-- CATALOG BACK MATTER (UNVERIFIED) | 2026-10-29 | READ ONLY | NO ARCHER RAW TABLES
-- Output: CONTENT_ID, SOURCE_TABLE_NAME, OSCAL_ELEMENT_PATH,
--         OSCAL_ELEMENT, ARCHER_FIELD_NAME, FIELD_VALUE
-- Field names are reconstructed from approved mapping identity or unique native
-- mappings, not automatically read from a universal Archer column in DIM.
-- Sample only; test in DEV and verify deployed mapping/registry before QA PASS.

-- 1: Back Matter resource rlinks: exploratory target-only scan.
-- The Archer field name CANNOT be recovered from a native resource payload
-- without verified mapping/lineage. 'UNVERIFIED' is intentional.
-- A zero-row result does not prove the source field was empty.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID,d.SOURCE_TABLE_NAME,
       'catalog.back-matter.resources[].rlinks' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'UNVERIFIED_SOURCE_LINKS' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:"rlinks" AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT d
WHERE d.ELEMENT_TYPE IN ('resources','resource')
  AND d.METADATA_JSON:"rlinks" IS NOT NULL
ORDER BY CONTENT_ID LIMIT 25;

-- 2: Back Matter resource base64: exploratory target-only scan.
-- The Archer field name CANNOT be recovered from a native resource payload
-- without verified mapping/lineage. 'UNVERIFIED' is intentional.
-- A zero-row result does not prove the source field was empty.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID,d.SOURCE_TABLE_NAME,
       'catalog.back-matter.resources[].base64' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'UNVERIFIED_ATTACHMENTS' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:"base64" AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT d
WHERE d.ELEMENT_TYPE IN ('resources','resource')
  AND d.METADATA_JSON:"base64" IS NOT NULL
ORDER BY CONTENT_ID LIMIT 25;
