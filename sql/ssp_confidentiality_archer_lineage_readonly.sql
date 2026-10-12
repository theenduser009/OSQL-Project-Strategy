-- SSP Archer confidentiality lineage | READ ONLY | 2026-10-12
-- This inspects the proposed source-field property convention.
-- Live presence and value-level attribution have not been verified.

-- 1. Find the Archer source-field lineage property.
SELECT
    p.SOURCE_RECORD_ID,
    p.METADATA_JSON:"name"::STRING AS PROP_NAME,
    p.METADATA_JSON:"value"::STRING AS ARCHER_FIELD_NAME
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT p
WHERE LOWER(p.ELEMENT_TYPE) = 'props'
  AND p.METADATA_JSON:"name"::STRING = 'source-field'
  AND p.METADATA_JSON:"value"::STRING =
      'RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY'
ORDER BY p.SOURCE_RECORD_ID
LIMIT 20;

-- 2. Compare the lineage property with its source record's OSCAL value.
-- This record-level join does not prove which of multiple source fields
-- contributed the final confidentiality value.
SELECT
    p.SOURCE_RECORD_ID,
    p.METADATA_JSON:"value"::STRING AS ARCHER_FIELD_NAME,
    s.METADATA_JSON:"security-objective-confidentiality"::STRING AS OSCAL_VALUE
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT p
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT s
    ON p.SOURCE_RECORD_ID = s.SOURCE_RECORD_ID
WHERE LOWER(p.ELEMENT_TYPE) = 'props'
  AND p.METADATA_JSON:"name"::STRING = 'source-field'
  AND p.METADATA_JSON:"value"::STRING =
      'RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY'
  AND LOWER(s.ELEMENT_TYPE) = 'security-impact-level'
ORDER BY p.SOURCE_RECORD_ID
LIMIT 20;
