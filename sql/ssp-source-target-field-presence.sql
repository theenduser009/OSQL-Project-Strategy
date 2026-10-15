-- Read-only source-field / persisted SSP payload presence diagnostic.
-- Run in a Snowflake SQL worksheet. Edit the SET values before execution.
-- Does not write source, registry, DIM or FACT data.
-- Diagnostic only: no exact owner/FACT lineage or per-record value equality check.
-- Source counts cover all available source rows, not a selected latest snapshot.
-- Samples are independent representatives and must not be compared as a matched pair.
-- Property names strip leading/trailing separators; source keys remain exact.
-- A found object is a candidate, not proof of correct mapping or namespace.
-- Populated-source detection is shallow: empty strings/arrays/objects are excluded.
-- Key-present counts include explicit JSON null; missing keys are distinct.
-- No Snowflake execution has been verified for this script.

SET raw_table = '<RAW_DATABASE>.<SOURCE_SCHEMA>.<SOURCE_TABLE>';
SET dim_table = '<CURATED_DATABASE>.<CURATED_SCHEMA>.<DIM_TABLE>';
SET source_system = '<SOURCE_SYSTEM>';
SET source_table_name = '<SOURCE_TABLE_NAME>';

WITH requested AS (
    -- Replace this example with your requested field list.
    SELECT column1::VARCHAR AS source_field,
           column2::VARCHAR AS mapping_status,
           column3::VARCHAR AS role_id
    FROM VALUES ('<SOURCE_FIELD>', '<MAPPING_STATUS>', NULL)
),
source_values AS (
    SELECT r.source_field, s.CONTENT_ID::VARCHAR AS content_id,
           GET(s.CURATED_JSON, r.source_field) AS source_value
    FROM IDENTIFIER($raw_table) s CROSS JOIN requested r
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
    FROM IDENTIFIER($dim_table)
    WHERE SOURCE_SYSTEM_NAME = $source_system
      AND SOURCE_TABLE_NAME = $source_table_name
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
