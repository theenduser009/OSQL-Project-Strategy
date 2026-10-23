-- SSP INFORMATION_SYSTEM_TYPE: Archer source -> persisted System Characteristics prop
-- Date: 2026-10-23
-- READ ONLY. Run in a Snowflake DEV SQL worksheet; no setup variables or writes.
--
-- Source One mapping CSV (APPROVED):
--   INFORMATION_SYSTEM_TYPE
--     -> system-security-plan.system-characteristics.props[]
--   transform=archer-select; null_policy=preserve
--   expected property name: information-system-type
--
-- Verify ownership through SSP DIM -> FACT -> props DIM; the property is
-- a child element, not necessarily inline in system-characteristics METADATA_JSON.
-- This checks field presence, the exact owning branch, and single-valued
-- Matillion-resolved picklist equality when such a label is available.
-- Multivalued/other source shapes require a separate value-level review.
-- Source RAW may contain multiple snapshots of one CONTENT_ID; results do not
-- replicate the notebook's latest-snapshot selection. No live run is asserted.

WITH system_characteristics_props AS (
    SELECT
        child.SOURCE_RECORD_ID,
        child.METADATA_JSON:"name"::STRING AS PROPERTY_NAME,
        child.METADATA_JSON:"value" AS TARGET_VALUE
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT parent
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY edge
      ON edge.FK_SOURCE_ELEMENT_HASH = parent.PK_OSCAL_SSP_ELEMENT_HASH
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT child
      ON child.PK_OSCAL_SSP_ELEMENT_HASH = edge.FK_TARGET_ELEMENT_HASH
    WHERE parent.ELEMENT_TYPE = 'system-characteristics'
      AND parent.SOURCE_SYSTEM_NAME = 'ARCHER'
      AND parent.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND child.ELEMENT_TYPE = 'props'
      AND child.SOURCE_SYSTEM_NAME = parent.SOURCE_SYSTEM_NAME
      AND child.SOURCE_TABLE_NAME = parent.SOURCE_TABLE_NAME
      AND child.SOURCE_RECORD_ID = parent.SOURCE_RECORD_ID
      AND child.METADATA_JSON:"name"::STRING = 'information-system-type'
),
source_values AS (
    SELECT
        s.CONTENT_ID::STRING AS CONTENT_ID,
        s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE" AS SOURCE_VALUE,
        CASE
            WHEN IS_NULL_VALUE(s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE")
                THEN 'EXPLICIT_JSON_NULL'
            WHEN TO_JSON(s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE") IN ('""', '[]', '{}')
                THEN 'EMPTY_SOURCE_VALUE'
            ELSE 'NON_NULL_SOURCE'
        END AS SOURCE_STATE,
        CASE
            WHEN IS_ARRAY(s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE":"ResolvedValues")
             AND ARRAY_SIZE(s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE":"ResolvedValues") = 1
                THEN s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE":"ResolvedValues"[0]:"ValueName"::STRING
            ELSE NULL
        END AS EXPECTED_SINGLE_LABEL
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW s
    -- SQL NULL: missing key. JSON null is included to check preserve policy.
    WHERE s.CURATED_JSON:"INFORMATION_SYSTEM_TYPE" IS NOT NULL
)
SELECT
    source.CONTENT_ID,
    source.SOURCE_STATE,
    source.SOURCE_VALUE,
    source.EXPECTED_SINGLE_LABEL,
    target.PROPERTY_NAME,
    target.TARGET_VALUE,
    CASE
        WHEN source.SOURCE_STATE = 'EMPTY_SOURCE_VALUE'
            THEN 'SOURCE_EMPTY_REVIEW'
        WHEN target.SOURCE_RECORD_ID IS NULL
            THEN 'MISSING_TARGET_PROPERTY'
        WHEN source.SOURCE_STATE = 'EXPLICIT_JSON_NULL'
         AND IS_NULL_VALUE(target.TARGET_VALUE)
            THEN 'EXPLICIT_NULL_PRESERVED'
        WHEN source.SOURCE_STATE = 'EXPLICIT_JSON_NULL'
            THEN 'SOURCE_NULL_TARGET_NOT_NULL'
        WHEN target.TARGET_VALUE IS NULL OR IS_NULL_VALUE(target.TARGET_VALUE)
            THEN 'TARGET_VALUE_MISSING_OR_NULL'
        WHEN source.EXPECTED_SINGLE_LABEL IS NOT NULL
         AND target.TARGET_VALUE::STRING = source.EXPECTED_SINGLE_LABEL
            THEN 'VALUE_MATCH'
        WHEN source.EXPECTED_SINGLE_LABEL IS NOT NULL
            THEN 'VALUE_MISMATCH'
        ELSE 'TARGET_PRESENT_REVIEW_MULTIVALUE_OR_SOURCE_SHAPE'
    END AS QA_STATUS
FROM source_values source
LEFT JOIN system_characteristics_props target
  ON target.SOURCE_RECORD_ID = source.CONTENT_ID
ORDER BY source.CONTENT_ID, target.TARGET_VALUE::STRING
LIMIT 100;
