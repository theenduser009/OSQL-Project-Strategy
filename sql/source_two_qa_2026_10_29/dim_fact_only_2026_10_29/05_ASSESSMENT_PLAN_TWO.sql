-- ASSESSMENT PLAN (SOURCE ONE) | 2026-10-29 | READ ONLY | NO ARCHER RAW TABLES
-- Output: CONTENT_ID, SOURCE_TABLE_NAME, OSCAL_ELEMENT_PATH,
--         OSCAL_ELEMENT, ARCHER_FIELD_NAME, FIELD_VALUE
-- Field names are reconstructed from approved mapping identity or unique native
-- mappings, not automatically read from a universal Archer column in DIM.
-- Sample only; test in DEV and verify deployed mapping/registry before QA PASS.

-- 1: Source One SAP exact field identity.
-- Source Two SAP persisted, but deployed Source Two mapping fields/fingerprints
-- were not provided; do not infer their Archer origins from props alone.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID, d.SOURCE_TABLE_NAME,
       'assessment-plan.tasks[].props[request-to-begin-assessment].value' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'REQUEST_TO_BEGIN_ASSESSMENT' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:value AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT d
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
  AND d.ELEMENT_TYPE='props'
  AND d.METADATA_JSON:name::VARCHAR='request-to-begin-assessment'
  AND d.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH = MD5_BINARY(
    'v1_registry_path_instance|ARCHER|'||d.SOURCE_TABLE_NAME||'|'||
    d.SOURCE_RECORD_ID||'|SECURITY_ASSESSMENT_PLAN|'||
    'assessment-plan.tasks[].props[]|REQUEST_TO_BEGIN_ASSESSMENT'
  )
ORDER BY CONTENT_ID LIMIT 25;

-- 2: Source One SAP exact field identity.
-- Source Two SAP persisted, but deployed Source Two mapping fields/fingerprints
-- were not provided; do not infer their Archer origins from props alone.
SELECT d.SOURCE_RECORD_ID AS CONTENT_ID, d.SOURCE_TABLE_NAME,
       'assessment-plan.tasks[].props[approval-to-begin-assessment].value' AS OSCAL_ELEMENT_PATH,
       d.ELEMENT_TYPE AS OSCAL_ELEMENT,
       'APPROVAL_TO_BEGIN_ASSESSMENT' AS ARCHER_FIELD_NAME,
       d.METADATA_JSON:value AS FIELD_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT d
WHERE d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
  AND d.ELEMENT_TYPE='props'
  AND d.METADATA_JSON:name::VARCHAR='approval-to-begin-assessment'
  AND d.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH = MD5_BINARY(
    'v1_registry_path_instance|ARCHER|'||d.SOURCE_TABLE_NAME||'|'||
    d.SOURCE_RECORD_ID||'|SECURITY_ASSESSMENT_PLAN|'||
    'assessment-plan.tasks[].props[]|APPROVAL_TO_BEGIN_ASSESSMENT'
  )
ORDER BY CONTENT_ID LIMIT 25;
