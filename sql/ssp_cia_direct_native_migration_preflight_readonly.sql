-- SSP CIA direct-native migration preflight | READ ONLY | 2026-10-12
-- This SQL does not modify DIM, FACT, mapping CSV, registry, or notebook state.
-- It inventories existing fallback props/edges prior to approved graph migration.
-- Exact Snowflake DEV names, no placeholders or source-record literals.

-- 1) Stored fallback value nodes and their existing incoming FACT links.
SELECT
    d.METADATA_JSON:"name"::STRING AS FALLBACK_FIELD,
    COUNT(*) AS STORED_FALLBACK_NODES,
    COUNT(DISTINCT d.SOURCE_RECORD_ID) AS SOURCE_RECORDS,
    COUNT(f.FK_TARGET_ELEMENT_HASH) AS STORED_INCOMING_LINKS
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT d
LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY f
    ON d.PK_OSCAL_SSP_ELEMENT_HASH = f.FK_TARGET_ELEMENT_HASH
WHERE LOWER(d.ELEMENT_TYPE) = 'props'
  AND d.METADATA_JSON:"name"::STRING IN (
    'recommended-confidentiality-control-category',
    'confidentiality-control-category-override',
    'recommended-integrity-control-category',
    'integrity-control-category-override',
    'recommended-availability-control-category',
    'availability-control-category-override',
    'programsite-integrity-control-category',
    'programsite-availability-control-category',
    'cnss-confidentiality-rating',
    'cnss-integrity-rating',
    'cnss-availability-rating'
  )
GROUP BY FALLBACK_FIELD
ORDER BY FALLBACK_FIELD;

-- 2) Current native security-impact coverage before installing the new mapper.
SELECT
    COUNT(*) AS STORED_NATIVE_IMPACT_NODES,
    COUNT(DISTINCT SOURCE_RECORD_ID) AS DISTINCT_SOURCE_RECORDS,
    COUNT_IF(
        METADATA_JSON:"security-objective-confidentiality" IS NOT NULL
        AND NOT IS_NULL_VALUE(METADATA_JSON:"security-objective-confidentiality")
    ) AS NON_NULL_CONFIDENTIALITY,
    COUNT_IF(
        METADATA_JSON:"security-objective-integrity" IS NOT NULL
        AND NOT IS_NULL_VALUE(METADATA_JSON:"security-objective-integrity")
    ) AS NON_NULL_INTEGRITY,
    COUNT_IF(
        METADATA_JSON:"security-objective-availability" IS NOT NULL
        AND NOT IS_NULL_VALUE(METADATA_JSON:"security-objective-availability")
    ) AS NON_NULL_AVAILABILITY
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
WHERE LOWER(ELEMENT_TYPE) = 'security-impact-level';

-- OBSOLETE_TARGET_ROWS_BLOCKED remains in the private guarded loader.
-- Do not drop, delete, merge, or reload based only on these counts.
