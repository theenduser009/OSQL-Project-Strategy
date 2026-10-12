-- SSP: show actual persisted source-field lineage props, no Archer field-name filter.
-- A null source value does not create a source-field prop in the current mapper.
SELECT
    SOURCE_RECORD_ID,
    METADATA_JSON:"name"::STRING AS PROP_NAME,
    METADATA_JSON:"value"::STRING AS ARCHER_FIELD_NAME,
    METADATA_JSON AS PROP_PAYLOAD
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
WHERE ELEMENT_TYPE = 'props'
  AND METADATA_JSON:"name"::STRING = 'source-field'
ORDER BY ARCHER_FIELD_NAME
LIMIT 100;
