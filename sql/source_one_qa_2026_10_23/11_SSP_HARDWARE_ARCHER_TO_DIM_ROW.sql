-- 2026-10-23 | READ ONLY | Snowflake DEV
-- Trace Archer HARDWARE[] ContentId references to exact SSP DIM components.
-- The DIM SOURCE_RECORD_ID is the Authorization Package Content ID.
-- ARCHER_FIELD_NAME is a query label; it is not stored as a DIM field.
-- Deterministic hash matches current v1_registry_path_instance code.
WITH archer AS (
    SELECT
        s.CONTENT_ID::STRING AS PACKAGE_CONTENT_ID,
        'HARDWARE' AS ARCHER_FIELD_NAME,
        s.CURATED_JSON:"HARDWARE" AS ARCHER_VALUE,
        IFF(
            IS_OBJECT(f.VALUE),
            f.VALUE:"ContentId"::STRING,
            f.VALUE::STRING
        ) AS HARDWARE_REF_ID
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW s,
         LATERAL FLATTEN(
             INPUT => s.CURATED_JSON:"HARDWARE"
         ) f
)
SELECT
    a.PACKAGE_CONTENT_ID,
    a.ARCHER_FIELD_NAME,
    a.ARCHER_VALUE,
    a.HARDWARE_REF_ID,
    d.SOURCE_RECORD_ID AS DIM_SOURCE_RECORD_ID,
    d.ELEMENT_TYPE,
    d.METADATA_JSON:"type"::STRING AS COMPONENT_TYPE,
    d.METADATA_JSON AS DIM_JSON,
    HEX_ENCODE(d.PK_OSCAL_SSP_ELEMENT_HASH) AS DIM_HASH
FROM archer a
LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT d
    ON d.PK_OSCAL_SSP_ELEMENT_HASH = MD5_BINARY(
        CONCAT_WS('|',
            'v1_registry_path_instance',
            'ARCHER',
            'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW',
            a.PACKAGE_CONTENT_ID,
            'SSP',
            'system-security-plan.system-implementation.components[]',
            a.HARDWARE_REF_ID
        )
    )
    AND d.ELEMENT_TYPE = 'components'
    AND d.SOURCE_RECORD_ID = a.PACKAGE_CONTENT_ID
ORDER BY a.PACKAGE_CONTENT_ID;
