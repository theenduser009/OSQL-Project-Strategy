-- CATALOG METADATA QA | DEV | READ-ONLY | 2026-10-22
-- Copy into Snowflake worksheet. Change ONLY the two table paths below.
-- Paths use DATABASE.SCHEMA.TABLE; no internal object names stored in public Git.
-- This checks persisted DIM, not uncommitted mapper PREVIEW.
SET QA_SOURCE_RAW = 'REPLACE_DATABASE.SCHEMA.SOURCE_RAW_TABLE';
SET QA_CATALOG_DIM = 'REPLACE_DATABASE.SCHEMA.CATALOG_DIM_TABLE';

WITH fields AS (
  SELECT column1::VARCHAR AS source_field, column2::VARCHAR AS oscal_member
  FROM VALUES ('SOURCE_NAME','title'),
              ('SOURCE_VERSION','version'),
              ('SOURCE_DESCRIPTION','remarks')
),
source_ids AS (
  SELECT TO_VARCHAR(CONTENT_ID) AS sid,
         COUNT(DISTINCT COALESCE(TO_JSON(CURATED_JSON),'<SQL_NULL>')) AS payload_versions,
         ANY_VALUE(CURATED_JSON) AS source_json
  FROM IDENTIFIER($QA_SOURCE_RAW)
  WHERE CONTENT_ID IS NOT NULL
  GROUP BY TO_VARCHAR(CONTENT_ID)
),
target_ids AS (
  SELECT TO_VARCHAR(SOURCE_RECORD_ID) AS sid,
         COUNT(*) AS target_rows, ANY_VALUE(METADATA_JSON) AS target_json
  FROM IDENTIFIER($QA_CATALOG_DIM)
  WHERE UPPER(SOURCE_SYSTEM_NAME)='ARCHER'
    AND UPPER(SOURCE_TABLE_NAME)=UPPER(SPLIT_PART($QA_SOURCE_RAW,'.',3))
    AND LOWER(ELEMENT_TYPE)='metadata'
    AND SOURCE_RECORD_ID IS NOT NULL
  GROUP BY TO_VARCHAR(SOURCE_RECORD_ID)
),
paired AS (
  SELECT COALESCE(s.sid,t.sid) AS sid,
         s.sid IS NOT NULL AS source_exists,
         t.sid IS NOT NULL AS target_exists,
         s.payload_versions, t.target_rows, s.source_json, t.target_json
  FROM source_ids s FULL OUTER JOIN target_ids t ON s.sid=t.sid
),
values_by_field AS (
  SELECT p.*, f.source_field, f.oscal_member,
         IFF(TYPEOF(p.source_json)='OBJECT',
             GET(p.source_json,f.source_field),NULL::VARIANT) AS source_value,
         IFF(TYPEOF(p.target_json)='OBJECT',
             GET(p.target_json,f.oscal_member),NULL::VARIANT) AS target_value
  FROM paired p CROSS JOIN fields f
),
checks AS (
  SELECT *,
         CASE
           WHEN NOT source_exists THEN 'TARGET_ONLY_ID'
           WHEN payload_versions>1 THEN 'RAW_VERSIONS_AMBIGUOUS'
           WHEN TYPEOF(source_json)<>'OBJECT' THEN 'RAW_JSON_WRONG_SHAPE'
           WHEN source_value IS NULL OR IS_NULL_VALUE(source_value)
             THEN 'SOURCE_UNPOPULATED'
           WHEN TYPEOF(source_value)<>'VARCHAR'
             THEN 'SOURCE_VALUE_WRONG_SHAPE'
           WHEN TRIM(source_value::VARCHAR)='' THEN 'SOURCE_UNPOPULATED'
           WHEN NOT target_exists THEN 'TARGET_METADATA_MISSING'
           WHEN target_rows<>1 THEN 'TARGET_METADATA_DUPLICATE'
           WHEN TYPEOF(target_json)<>'OBJECT' THEN 'TARGET_JSON_WRONG_SHAPE'
           WHEN target_value IS NULL OR IS_NULL_VALUE(target_value)
             THEN 'TARGET_VALUE_MISSING'
           WHEN TYPEOF(target_value)<>'VARCHAR'
             THEN 'TARGET_VALUE_WRONG_SHAPE'
           WHEN TRIM(target_value::VARCHAR)='' THEN 'TARGET_VALUE_MISSING'
           WHEN source_value::VARCHAR=target_value::VARCHAR THEN 'EXACT_MATCH'
           ELSE 'VALUE_MISMATCH'
         END AS result
  FROM values_by_field
),
field_counts AS (
  SELECT source_field,oscal_member,
         COUNT_IF(source_exists) AS source_ids,
         COUNT_IF(target_exists) AS persisted_target_ids,
         COUNT_IF(result='EXACT_MATCH') AS exact_matches,
         COUNT_IF(result='SOURCE_UNPOPULATED') AS source_without_value,
         COUNT_IF(result='RAW_VERSIONS_AMBIGUOUS') AS ambiguous_raw_ids,
         COUNT_IF(result IN ('RAW_JSON_WRONG_SHAPE','SOURCE_VALUE_WRONG_SHAPE'))
           AS invalid_source_shape,
         COUNT_IF(result='TARGET_METADATA_MISSING') AS missing_target_metadata,
         COUNT_IF(result='TARGET_VALUE_MISSING') AS missing_target_value,
         COUNT_IF(result='VALUE_MISMATCH') AS wrong_target_value,
         COUNT_IF(result IN ('TARGET_METADATA_DUPLICATE','TARGET_JSON_WRONG_SHAPE',
                             'TARGET_VALUE_WRONG_SHAPE')) AS target_shape_or_dup,
         COUNT_IF(result='TARGET_ONLY_ID') AS target_only_ids
  FROM checks GROUP BY source_field,oscal_member
),
sample_ids AS (
  SELECT sid,LEFT(SHA2(sid,256),12) AS sample_key,
         ROW_NUMBER() OVER(
           ORDER BY MAX(IFF(result='EXACT_MATCH',0,1)) DESC,SHA2(sid,256)
         ) AS sample_rank
  FROM checks WHERE source_exists AND target_exists
  GROUP BY sid
  QUALIFY sample_rank<=15
),
samples AS (
  SELECT k.sample_rank,k.sample_key,
         MAX(IFF(c.source_field='SOURCE_NAME',c.result,NULL)) AS name_result,
         MAX(IFF(c.source_field='SOURCE_VERSION',c.result,NULL)) AS version_result,
         MAX(IFF(c.source_field='SOURCE_DESCRIPTION',c.result,NULL)) AS description_result
  FROM sample_ids k JOIN checks c ON c.sid=k.sid
  GROUP BY k.sample_rank,k.sample_key
)
SELECT 0 AS sort_key,'FIELD_SUMMARY' AS row_type,
       source_field,oscal_member,
       source_ids,persisted_target_ids,exact_matches,source_without_value,
       ambiguous_raw_ids,invalid_source_shape,missing_target_metadata,
       missing_target_value,wrong_target_value,target_shape_or_dup,target_only_ids,
       NULL::VARCHAR AS sample_key,NULL::VARCHAR AS name_result,
       NULL::VARCHAR AS version_result,NULL::VARCHAR AS description_result,
       NULL::NUMBER AS sample_rank
FROM field_counts
UNION ALL
SELECT 1,'MATCHED_SAMPLE',NULL::VARCHAR,NULL::VARCHAR,
       NULL::NUMBER,NULL::NUMBER,NULL::NUMBER,NULL::NUMBER,
       NULL::NUMBER,NULL::NUMBER,NULL::NUMBER,NULL::NUMBER,
       NULL::NUMBER,NULL::NUMBER,
       sample_key,name_result,version_result,description_result,sample_rank
FROM samples
ORDER BY sort_key,source_field,sample_rank;

-- Expected: 3 field summary rows and up to 15 matched-ID status samples.
-- Source without data is not a mapping failure. An exact mismatch can mean
-- current RAW is newer than the stored release. A sample_key is pseudonymous.
-- Do not use this result as evidence that the latest PREVIEW was committed.
