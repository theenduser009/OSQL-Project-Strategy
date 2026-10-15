-- Mapping statuses reflect owner-approved repository metadata on 2026-10-15.
-- Deployment to Snowflake and target-value verification are still pending.
-- Read-only source-field / persisted SSP payload presence diagnostic.
-- Paste the entire SELECT into a Snowflake SQL worksheet and run it.
-- Does not write source, registry, DIM or FACT data.
-- Diagnostic only: no exact owner/FACT lineage or per-record value equality check.
-- Source counts cover all available source rows, not a selected latest snapshot.
-- Samples are independent representatives and must not be compared as a matched pair.
-- Property names strip leading/trailing separators; source keys remain exact.
-- A found object is a candidate, not proof of correct mapping or namespace.
-- Populated-source detection is shallow: empty strings/arrays/objects are excluded.
-- Key-present counts include explicit JSON null; missing keys are distinct.
-- No Snowflake execution has been verified for this script.

WITH requested AS (
    SELECT column1::VARCHAR AS source_field,
           column2::VARCHAR AS mapping_status,
           column3::VARCHAR AS role_id
    FROM VALUES
      ('ALLOCATE_BASELINE_CONTROLS', 'APPROVED', NULL),
      ('ARCHIVE_CONTROLS', 'APPROVED', NULL),
      ('BASELINE_CONTROLS_ALLOCATED_DATE', 'APPROVED', NULL),
      ('FULL_CONTROL_ASSESSMENT_HELPER', 'APPROVED', NULL),
      ('CONTROL_RISK_APPETITE', 'APPROVED', NULL),
      ('PCT_CURRENT_CONTROL_RISK_THRESHOLD', 'APPROVED', NULL),
      ('CONTROL_RISK_THRESHOLD_HELPER', 'APPROVED', NULL),
      ('COUNT_OF_CONTROLS_NOT_ASSESSED', 'APPROVED', NULL),
      ('COUNT_OF_INHERITED_CONTROLS_THAT_HAVE_BEEN_ARCHIVED', 'APPROVED', NULL),
      ('PCT_OF_SATISFIED_CONTROLS', 'APPROVED', NULL),
      ('SECURITY_CONTROL_ASSESSOR_SCA', 'APPROVED', 'security-control-assessor'),
      ('LINK_CNSS_CONTROLS_BY_CONFIDENTIALITY_RATING', 'APPROVED', NULL),
      ('LINK_CNSS_CONTROLS_BY_INTEGRITY_RATING', 'APPROVED', NULL),
      ('LINK_CNSS_CONTROLS_BY_AVAILABILITY_RATING', 'APPROVED', NULL),
      ('HELPER_ALLOCATED_CONTROLS', 'APPROVED', NULL),
      ('PRECONTROL_ALLOCATION_PROGRESS_VIEW', 'APPROVED', NULL),
      ('EXPORT_CONTROLLED_DATA_ITARAR_IF_APPLICABLE', 'APPROVED', NULL),
      ('ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA', 'APPROVED', 'alternate-security-control-assessor'),
      ('HELPER_OTS_CONTROLS', 'APPROVED', NULL),
      ('DATE_CONTINUE_TO_CONTROL_IMPLEMENTATION', 'APPROVED', NULL),
      ('_CURRENT_CONTROL_RISK_THRESHOLD', 'APPROVED', NULL),
      ('_OF_SATISFIED_CONTROLS', 'APPROVED', NULL)
),
source_values AS (
    SELECT r.source_field, s.CONTENT_ID::VARCHAR AS content_id,
           GET(s.CURATED_JSON, r.source_field) AS source_value
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW s CROSS JOIN requested r
),
source_stats AS (
    SELECT source_field,
           COUNT(DISTINCT IFF(source_value IS NOT NULL, content_id, NULL))
               AS source_key_present_ids,
           COUNT(DISTINCT IFF(
               source_value IS NOT NULL AND NOT IS_NULL_VALUE(source_value)
               AND TRIM(TO_JSON(source_value)) NOT IN ('""', '[]', '{}'),
               content_id, NULL)) AS source_populated_ids,
           MAX(TO_JSON(source_value)) AS sample_source_value
    FROM source_values GROUP BY source_field
),
dim AS (
    SELECT SOURCE_RECORD_ID::VARCHAR AS content_id,
           ELEMENT_TYPE, METADATA_JSON
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
    WHERE SOURCE_SYSTEM_NAME = 'ARCHER'
      AND SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
),
objects AS (
    SELECT content_id, ELEMENT_TYPE, '$' AS json_path, METADATA_JSON AS obj
    FROM dim
    UNION ALL
    SELECT d.content_id, d.ELEMENT_TYPE, f.PATH::VARCHAR, f.VALUE
    FROM dim d,
         LATERAL FLATTEN(INPUT => d.METADATA_JSON, RECURSIVE => TRUE) f
    WHERE IS_OBJECT(f.VALUE)
),
target_stats AS (
    SELECT r.source_field,
           COUNT(DISTINCT o.content_id) AS target_found_ids,
           MAX(o.ELEMENT_TYPE || ':' || o.json_path) AS sample_target_location,
           MAX(TO_JSON(o.obj)) AS sample_target_object
    FROM requested r
    JOIN objects o ON (
        r.role_id IS NULL
        AND o.obj:"name"::VARCHAR =
            TRIM(REGEXP_REPLACE(LOWER(r.source_field), '[^a-z0-9]+', '-'), '-')
        AND ARRAY_CONTAINS(TO_VARIANT('value'), OBJECT_KEYS(o.obj))
    ) OR (
        r.role_id IS NOT NULL
        AND o.obj:"role-id"::VARCHAR = r.role_id
        AND ARRAY_SIZE(o.obj:"party-uuids") > 0
    )
    GROUP BY r.source_field
)
SELECT r.source_field, r.mapping_status,
       COALESCE(s.source_key_present_ids, 0) AS source_key_present_ids,
       COALESCE(s.source_populated_ids, 0) AS source_populated_ids,
       COALESCE(t.target_found_ids, 0) AS target_found_ids,
       s.sample_source_value, t.sample_target_location, t.sample_target_object
FROM requested r
LEFT JOIN source_stats s USING (source_field)
LEFT JOIN target_stats t USING (source_field)
ORDER BY r.mapping_status, r.source_field;
