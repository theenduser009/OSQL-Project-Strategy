-- OSCAL SSP security-impact coverage and Archer lineage checks
-- Date: 2026-10-12 | READ ONLY | Snowflake DEV
-- Public copy-and-run version: exact table names; no source-record identifiers.
-- NOTE: lineage is captured for contributing fields, not every null Archer key.
-- No live Snowflake execution is claimed by this publication.

-- 1. Check all approved CIA source fields: JSON nulls vs non-null source
--    values, and the number of stored source-field lineage properties.
WITH expected_fields (ARCHER_FIELD) AS (
    SELECT COLUMN1 FROM VALUES
        ('RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY'),
        ('CONFIDENTIALITY_CONTROL_CATEGORY_OVERRIDE'),
        ('RECOMMENDED_INTEGRITY_CONTROL_CATEGORY'),
        ('INTEGRITY_CONTROL_CATEGORY_OVERRIDE'),
        ('RECOMMENDED_AVAILABILITY_CONTROL_CATEGORY'),
        ('AVAILABILITY_CONTROL_CATEGORY_OVERRIDE'),
        ('PROGRAMSITE_INTEGRITY_CONTROL_CATEGORY'),
        ('PROGRAMSITE_AVAILABILITY_CONTROL_CATEGORY'),
        ('CNSS_CONFIDENTIALITY_RATING'),
        ('CNSS_INTEGRITY_RATING'),
        ('CNSS_AVAILABILITY_RATING')
),
source_counts AS (
    SELECT
        f.KEY::STRING AS ARCHER_FIELD,
        COUNT(*) AS SOURCE_FIELD_ROWS,
        COUNT_IF(IS_NULL_VALUE(f.VALUE)) AS JSON_NULL_ROWS,
        COUNT_IF(NOT IS_NULL_VALUE(f.VALUE) AND f.VALUE IS NOT NULL) AS NON_NULL_ROWS
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW a,
         LATERAL FLATTEN(INPUT => a.CURATED_JSON) f
    WHERE f.KEY::STRING IN (SELECT ARCHER_FIELD FROM expected_fields)
    GROUP BY 1
),
lineage_counts AS (
    SELECT
        METADATA_JSON:"value"::STRING AS ARCHER_FIELD,
        COUNT(*) AS LINEAGE_PROP_ROWS
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
    WHERE LOWER(ELEMENT_TYPE) = 'props'
      AND METADATA_JSON:"name"::STRING = 'source-field'
    GROUP BY 1
)
SELECT
    e.ARCHER_FIELD,
    COALESCE(s.SOURCE_FIELD_ROWS, 0) AS SOURCE_FIELD_ROWS,
    COALESCE(s.JSON_NULL_ROWS, 0) AS JSON_NULL_ROWS,
    COALESCE(s.NON_NULL_ROWS, 0) AS NON_NULL_ROWS,
    COALESCE(l.LINEAGE_PROP_ROWS, 0) AS LINEAGE_PROP_ROWS
FROM expected_fields e
LEFT JOIN source_counts s ON s.ARCHER_FIELD = e.ARCHER_FIELD
LEFT JOIN lineage_counts l ON l.ARCHER_FIELD = e.ARCHER_FIELD
ORDER BY e.ARCHER_FIELD;

-- 2. Find records containing non-null CIA source fields but no native
--    security-impact-level node. A native node can be absent legitimately
--    when incomplete objectives are preserved as sibling fallback props.
WITH source_counts AS (
    SELECT
        a.CONTENT_ID::STRING AS SOURCE_RECORD_ID,
        COUNT_IF(NOT IS_NULL_VALUE(f.VALUE) AND f.VALUE IS NOT NULL) AS NON_NULL_CIA_FIELDS
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW a,
         LATERAL FLATTEN(INPUT => a.CURATED_JSON) f
    WHERE f.KEY::STRING IN (
        'RECOMMENDED_CONFIDENTIALITY_CONTROL_CATEGORY',
        'CONFIDENTIALITY_CONTROL_CATEGORY_OVERRIDE',
        'RECOMMENDED_INTEGRITY_CONTROL_CATEGORY',
        'INTEGRITY_CONTROL_CATEGORY_OVERRIDE',
        'RECOMMENDED_AVAILABILITY_CONTROL_CATEGORY',
        'AVAILABILITY_CONTROL_CATEGORY_OVERRIDE',
        'PROGRAMSITE_INTEGRITY_CONTROL_CATEGORY',
        'PROGRAMSITE_AVAILABILITY_CONTROL_CATEGORY',
        'CNSS_CONFIDENTIALITY_RATING',
        'CNSS_INTEGRITY_RATING',
        'CNSS_AVAILABILITY_RATING'
    )
    GROUP BY 1
),
target_counts AS (
    SELECT
        SOURCE_RECORD_ID,
        COUNT_IF(LOWER(ELEMENT_TYPE) = 'security-impact-level') AS NATIVE_IMPACT_ROWS,
        COUNT_IF(
            LOWER(ELEMENT_TYPE) = 'props'
            AND METADATA_JSON:"name"::STRING IN (
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
        ) AS CIA_FALLBACK_PROPS
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
    GROUP BY 1
)
SELECT
    s.SOURCE_RECORD_ID,
    s.NON_NULL_CIA_FIELDS,
    COALESCE(t.NATIVE_IMPACT_ROWS, 0) AS NATIVE_IMPACT_ROWS,
    COALESCE(t.CIA_FALLBACK_PROPS, 0) AS CIA_FALLBACK_PROPS
FROM source_counts s
LEFT JOIN target_counts t
    ON s.SOURCE_RECORD_ID = t.SOURCE_RECORD_ID
WHERE s.NON_NULL_CIA_FIELDS > 0
  AND COALESCE(t.NATIVE_IMPACT_ROWS, 0) = 0
ORDER BY s.SOURCE_RECORD_ID
LIMIT 100;
