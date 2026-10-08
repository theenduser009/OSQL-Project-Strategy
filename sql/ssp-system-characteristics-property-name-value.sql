-- READ ONLY: OSCAL SSP system-characteristics property names and values.
-- Set target physical names from the CURRENT matched SSP storage contract.
-- Change only the placeholders below to your environment.
-- Do not infer source column identity from normalized property names alone;
-- use the approved runtime mapping SOURCE_FIELD_NAME -> OSCAL_ELEMENT_PATH.

SET SSP_DIM_TABLE = '<CURATED_DATABASE>.<CURATED_SCHEMA>.DIM_OSCAL_SSP_ELEMENT';
SET SSP_FACT_TABLE = '<CURATED_DATABASE>.<CURATED_SCHEMA>.FACT_OSCAL_SSP_DEPENDENCY';
SET OSCAL_PROPERTY_NAME = '<OSCAL_PROPERTY_NAME>'; -- e.g., "example-property"

SELECT
    sc.SOURCE_RECORD_ID,
    p.METADATA_JSON:"name"::STRING AS OSCAL_PROPERTY_NAME,
    p.METADATA_JSON:"value" AS OSCAL_PROPERTY_VALUE
FROM IDENTIFIER($SSP_DIM_TABLE) sc
JOIN IDENTIFIER($SSP_FACT_TABLE) f
    ON f.FK_SOURCE_ELEMENT_HASH = sc.PK_OSCAL_SSP_ELEMENT_HASH
   AND f.DEPENDENCY_TYPE = 'CONTAINS'
JOIN IDENTIFIER($SSP_DIM_TABLE) p
    ON p.PK_OSCAL_SSP_ELEMENT_HASH = f.FK_TARGET_ELEMENT_HASH
WHERE sc.ELEMENT_TYPE = 'system-characteristics'
  AND p.ELEMENT_TYPE = 'props'
  AND sc.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID
  AND p.METADATA_JSON:"name"::STRING = $OSCAL_PROPERTY_NAME
ORDER BY sc.SOURCE_RECORD_ID
LIMIT 25;

-- Exact source-field name:
-- Read SOURCE_FIELD_NAME and OSCAL_ELEMENT_PATH from the approved mapping CSV.
-- Example normalized property name does not independently prove Archer Field ID.
-- Source value is available in the frozen source's CURATED_JSON at SOURCE_FIELD_NAME.
-- For native implemented-requirement values use control-id and remarks instead.
-- For responsible parties use role-id, party-uuids and parties UUIDs instead.
