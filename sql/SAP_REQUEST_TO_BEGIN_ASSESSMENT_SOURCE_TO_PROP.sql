-- Assessment Plan: REQUEST_TO_BEGIN_ASSESSMENT source-to-target value QA
-- Evidence date: 2026-10-23 | READ ONLY | Snowflake DEV | No variables or DML
--
-- Current source-one Mapping/ARCHER_OSCAL_MAPPINGS.csv (checked at
-- private OSCAL repo commit 518dc71de73fdf7b39fba386cea3f9166c4590c1):
--   source: REQUEST_TO_BEGIN_ASSESSMENT
--   model: SECURITY_ASSESSMENT_PLAN
--   target: assessment-plan.tasks[].props[]
--   expected property name: request-to-begin-assessment
--   status: APPROVED | transform: archer-select | null policy: preserve
--
-- Task and property are separate DIM elements. Two FACT CONTAINS links
-- establish assessment-plan root -> tasks -> props ownership.
-- Results are persisted target inspections, NOT evidence of this script
-- performing a mapper PREVIEW or COMMIT.
--
-- Important limits:
-- * RAW may contain multiple snapshots per Content ID. This report does not
--   implement the mapper's full latest-source-row selection.
-- * A single matched curated ResolvedValues label is compared where possible.
--   Multi-select/unresolved/other shapes are explicitly flagged for review.
-- * Running this read-only QA has no effect on DIM, FACT, or registry tables.

WITH task_properties AS (
    SELECT
        prop.SOURCE_RECORD_ID,
        task.METADATA_JSON:"title"::STRING AS TASK_TITLE,
        prop.METADATA_JSON:"name"::STRING AS PROPERTY_NAME,
        prop.METADATA_JSON:"value" AS TARGET_VALUE,
        COUNT(*) OVER (
            PARTITION BY prop.SOURCE_RECORD_ID, prop.METADATA_JSON:"name"::STRING
        ) AS PROPERTY_OCCURRENCES
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT root
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_ASSESSMENT_PLAN_DEPENDENCY task_link
      ON task_link.FK_SOURCE_ELEMENT_HASH = root.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH
     AND task_link.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT task
      ON task.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH = task_link.FK_TARGET_ELEMENT_HASH
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_ASSESSMENT_PLAN_DEPENDENCY prop_link
      ON prop_link.FK_SOURCE_ELEMENT_HASH = task.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH
     AND prop_link.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT prop
      ON prop.PK_DIM_OSCAL_ASSESSMENT_PLAN_ELEMENT_HASH = prop_link.FK_TARGET_ELEMENT_HASH
    WHERE root.ELEMENT_TYPE = 'assessment-plan'
      AND task.ELEMENT_TYPE = 'tasks'
      AND prop.ELEMENT_TYPE = 'props'
      AND root.SOURCE_SYSTEM_NAME = 'ARCHER'
      AND root.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND task.SOURCE_SYSTEM_NAME = root.SOURCE_SYSTEM_NAME
      AND task.SOURCE_TABLE_NAME = root.SOURCE_TABLE_NAME
      AND task.SOURCE_RECORD_ID = root.SOURCE_RECORD_ID
      AND prop.SOURCE_SYSTEM_NAME = root.SOURCE_SYSTEM_NAME
      AND prop.SOURCE_TABLE_NAME = root.SOURCE_TABLE_NAME
      AND prop.SOURCE_RECORD_ID = root.SOURCE_RECORD_ID
      AND prop.METADATA_JSON:"name"::STRING = 'request-to-begin-assessment'
),
source_rows AS (
    SELECT
        s.CONTENT_ID::STRING AS CONTENT_ID,
        s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT" AS SOURCE_VALUE,
        CASE
            WHEN IS_NULL_VALUE(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT")
                THEN 'EXPLICIT_JSON_NULL'
            WHEN TO_JSON(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT") IN ('""', '[]', '{}')
                THEN 'EMPTY_SOURCE_VALUE'
            WHEN IS_OBJECT(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT")
             AND IS_ARRAY(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues")
             AND ARRAY_SIZE(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues") = 0
                THEN 'EMPTY_SOURCE_VALUE'
            ELSE 'NON_NULL_SOURCE'
        END AS SOURCE_STATE,
        CASE
            WHEN IS_OBJECT(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT")
             AND IS_ARRAY(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues")
             AND ARRAY_SIZE(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues") = 1
             AND IS_ARRAY(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ValuesListIds")
             AND ARRAY_SIZE(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ValuesListIds") = 1
             AND s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues"[0]:"LookupStatus"::STRING = 'MATCHED'
             AND s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues"[0]:"ValueId"::STRING =
                 s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ValuesListIds"[0]::STRING
                THEN s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT":"ResolvedValues"[0]:"ValueName"::STRING
            WHEN TYPEOF(s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT")
                 IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE', 'BOOLEAN')
                THEN s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT"::STRING
            ELSE NULL
        END AS EXPECTED_SINGLE_LABEL
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW s
    -- Excludes absent keys (SQL NULL); includes explicit JSON nulls.
    WHERE s.CURATED_JSON:"REQUEST_TO_BEGIN_ASSESSMENT" IS NOT NULL
),
qa AS (
    SELECT
        source.CONTENT_ID,
        source.SOURCE_STATE,
        source.SOURCE_VALUE,
        source.EXPECTED_SINGLE_LABEL,
        target.TASK_TITLE,
        target.PROPERTY_NAME,
        target.TARGET_VALUE,
        CASE
            WHEN source.SOURCE_STATE = 'EMPTY_SOURCE_VALUE'
                THEN 'SOURCE_EMPTY_REVIEW'
            WHEN target.SOURCE_RECORD_ID IS NULL
                THEN 'MISSING_TARGET_PROPERTY'
            WHEN target.PROPERTY_OCCURRENCES > 1
                THEN 'DUPLICATE_TARGET_PROPERTY'
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
    FROM source_rows source
    LEFT JOIN task_properties target
      ON target.SOURCE_RECORD_ID = source.CONTENT_ID
)
SELECT
    CONTENT_ID,
    SOURCE_STATE,
    SOURCE_VALUE,
    EXPECTED_SINGLE_LABEL,
    TASK_TITLE,
    PROPERTY_NAME,
    TARGET_VALUE,
    QA_STATUS,
    COUNT(*) OVER (PARTITION BY QA_STATUS) AS QA_STATUS_ROWS_ALL,
    COUNT(*) OVER () AS QA_ROWS_ALL
FROM qa
ORDER BY CONTENT_ID, QA_STATUS
LIMIT 100;
