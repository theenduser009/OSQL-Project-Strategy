-- OCT 29 2026: SQL 18, read-only Matillion / policy reference diagnostic.
-- Purpose: distinguish JSON array of numeric IDs from array of {ContentId,LevelId}
-- and check evidence of post-RAW field mapping and metadata enrichment.
-- THIS DOES NOT prove which particular Matillion UPDATE statement was deployed.
-- Repo code inspected: simplify-metadata-boundary @ c0fe30f030d2340b92199aeeb7ef42f2202ddd4a
-- Matillion candidate from 2026-10-01 only enriches UserList, ValuesListIds,
-- GroupList; it does not resolve policy record {ContentId,LevelId} into names.
-- Historical screenshots of a SELECT query are not proof UPDATE ran on all records.
--
-- Query 1 (STANDALONE, 2nd correction): no RESULT_SCAN and no
-- POLICY_CONTENT_ID, ACTUAL_ARCHER_FIELD or previous-result assumptions.
-- FIRST replace exactly one placeholder below with the real table name from
-- the FROM clause of the SUCCESSFUL SQL16 Query4-generated policy SELECT.
-- Do NOT invent the policy table: copy its exact RTX_RAW_DEV.ES_ESC_GRC name.
-- Once replaced, run THIS ONE SELECT directly for stored Content ID 7250127.
-- Valid for a table with CONTENT_ID and CURATED_JSON (verified by SQL16 Query4).
WITH policy_record AS (
  SELECT CONTENT_ID::VARCHAR AS RECORD_ID,
         IFF(TYPEOF(CURATED_JSON)='VARCHAR',
             TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON)),CURATED_JSON) AS J
  FROM IDENTIFIER(
    'RTX_RAW_DEV.ES_ESC_GRC.REPLACE_WITH_REAL_POLICY_TABLE_FROM_SQL16_QUERY4'
  )
  WHERE CONTENT_ID::VARCHAR='7250127'
),
field_value AS (
  SELECT RECORD_ID,
         GET(J,'CONTROL_TESTING_RESULTS_POLICY_LEVEL_1') AS STORED_VALUE
  FROM policy_record
),
parsed AS (
  SELECT RECORD_ID, STORED_VALUE,
         COALESCE(TRY_PARSE_JSON(STORED_VALUE::VARCHAR),
                  STORED_VALUE) AS PARSED_VALUE
  FROM field_value
),
items AS (
  SELECT p.RECORD_ID, TYPEOF(p.PARSED_VALUE) AS FIELD_TYPE,
         ref.INDEX AS MEMBER_INDEX,ref.VALUE AS MEMBER,
         TYPEOF(ref.VALUE) AS MEMBER_TYPE
  FROM parsed p,
       LATERAL FLATTEN(INPUT=>IFF(IS_ARRAY(p.PARSED_VALUE),
                                   p.PARSED_VALUE,ARRAY_CONSTRUCT()),
                       OUTER=>TRUE) ref
)
SELECT RECORD_ID AS POLICY_CONTENT_ID,
       'CONTROL_TESTING_RESULTS_POLICY_LEVEL_1' AS ARCHER_FIELD_NAME,
       FIELD_TYPE, MEMBER_INDEX, MEMBER_TYPE,
       MEMBER AS ORIGINAL_ARRAY_ITEM,
       IFF(IS_OBJECT(MEMBER),GET(MEMBER,'ContentId')::VARCHAR,NULL)
         AS OBJECT_CONTENT_ID,
       IFF(IS_OBJECT(MEMBER),GET(MEMBER,'LevelId')::VARCHAR,NULL)
         AS OBJECT_LEVEL_ID,
       IFF(MEMBER_TYPE IN ('INTEGER','DECIMAL','VARCHAR'),MEMBER::VARCHAR,NULL)
         AS SCALAR_ID_CANDIDATE,
       CASE
         WHEN MEMBER_TYPE='OBJECT' AND GET(MEMBER,'ContentId') IS NOT NULL
              AND GET(MEMBER,'LevelId') IS NOT NULL
           THEN 'OBJECT_CONTENTID_LEVELID_UNRESOLVED'
         WHEN MEMBER_TYPE IN ('INTEGER','DECIMAL')
           THEN 'NUMERIC_ID_CANDIDATE_LEVEL_UNKNOWN'
         WHEN MEMBER_TYPE='VARCHAR' AND TRY_TO_NUMBER(MEMBER::VARCHAR) IS NOT NULL
           THEN 'NUMERIC_STRING_CANDIDATE_LEVEL_UNKNOWN'
         WHEN MEMBER IS NULL AND FIELD_TYPE='ARRAY'
           THEN 'EMPTY_ARRAY'
         WHEN MEMBER IS NULL THEN 'FIELD_ABSENT_OR_NOT_ARRAY'
         ELSE 'OTHER_ITEM_TYPE'
       END AS REFERENCE_CLASS
FROM items
ORDER BY POLICY_CONTENT_ID,MEMBER_INDEX
LIMIT 300;

-- Query 2: Show the exact Source Two SOURCE curated field shape for the example.
-- This distinguishes a preserved reference object from select-list metadata.
-- Does NOT prove a particular UPDATE ran; no audit timestamp/fingerprint here.
WITH s AS (
 SELECT CONTENT_ID::VARCHAR AS CONTENT_ID,
        IFF(TYPEOF(CURATED_JSON)='VARCHAR',
            TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON)), CURATED_JSON) AS J
 FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW
 WHERE CONTENT_ID::VARCHAR='185810'
)
SELECT CONTENT_ID,
       TYPEOF(J) AS CURATED_JSON_TYPE,
       'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS' AS ARCHER_FIELD,
       GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS') AS FIELD_VALUE,
       TYPEOF(GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS'))
          AS FIELD_VALUE_TYPE,
       GET(GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS'),'ResolvedValues')
          AS RESOLVED_SELECT_VALUES,
       GET(GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS'),'ResolvedUser')
          AS RESOLVED_USER
FROM s;

-- Query 3: Count actual evidence of Matillion metadata enrichment in SOURCE RAW.
-- The three supported metadata enrichments are only meaningful WHEN their
-- respective input containers exist and are non-empty. Zero evidence on this
-- subset does NOT establish the UPDATE failed across every source.
WITH source_rows AS (
 SELECT CONTENT_ID,
        IFF(TYPEOF(CURATED_JSON)='VARCHAR',
            TRY_PARSE_JSON(AS_VARCHAR(CURATED_JSON)), CURATED_JSON) AS J
 FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW
), fields AS (
 SELECT s.CONTENT_ID, f.KEY::VARCHAR AS FIELD_NAME, f.VALUE AS V
 FROM source_rows s,
      LATERAL FLATTEN(INPUT=>s.J) f
)
SELECT COUNT(DISTINCT CONTENT_ID) AS SOURCE_RECORDS,
       COUNT_IF(TYPEOF(V)='OBJECT' AND IS_ARRAY(V:ValuesListIds)
                AND ARRAY_SIZE(V:ValuesListIds)>0) AS SELECT_INPUT_FIELDS,
       COUNT_IF(TYPEOF(V)='OBJECT' AND IS_ARRAY(V:ResolvedValues)
                AND ARRAY_SIZE(V:ResolvedValues)>0) AS SELECT_ENRICHED_FIELDS,
       COUNT_IF(TYPEOF(V)='OBJECT' AND IS_ARRAY(V:UserList)
                AND ARRAY_SIZE(V:UserList)>0) AS USER_INPUT_FIELDS,
       COUNT_IF(TYPEOF(V)='OBJECT' AND IS_ARRAY(V:GroupList)
                AND ARRAY_SIZE(V:GroupList)>0) AS GROUP_INPUT_FIELDS,
       COUNT_IF(TYPEOF(V)='OBJECT' AND IS_ARRAY(V:ResolvedGroups)
                AND ARRAY_SIZE(V:ResolvedGroups)>0) AS GROUP_ENRICHED_FIELDS
FROM fields;

-- Query 4A (read-only): Snowflake QUERY_HISTORY from the CURRENT
-- DB's fully-qualified information schema. It searches last 7 days and is
-- subject to visibility of the active role. It can MISS Matillion service
-- user UPDATEs that the active role is not permitted to monitor.
-- Official Snowflake QUERY_HISTORY table function supports 7 days max.
-- Zero rows does NOT prove Matillion did not run.
SELECT QUERY_ID, START_TIME, QUERY_TYPE, EXECUTION_STATUS,
       LEFT(QUERY_TEXT,300) AS QUERY_TEXT_PREVIEW
FROM TABLE(RTX_RAW_DEV.INFORMATION_SCHEMA.QUERY_HISTORY(
  END_TIME_RANGE_START => DATEADD('HOUR',-24,CURRENT_TIMESTAMP()),
  RESULT_LIMIT => 10000
))
WHERE QUERY_TEXT ILIKE '%CURATED_JSON%'
  AND QUERY_TYPE IN ('UPDATE','MERGE')
ORDER BY START_TIME DESC
LIMIT 100;

-- Query 4B (OPTIONAL alternate): broader ACCOUNT_USAGE coverage for up
-- to 365 days, only if current role can SELECT SNOWFLAKE.ACCOUNT_USAGE.
-- This view has data latency, and a SELECT error may mean missing grants.
-- Does not establish deployed Matillion SQL unless query text/run ID matches.
SELECT QUERY_ID, START_TIME, QUERY_TYPE, EXECUTION_STATUS,
       ROWS_UPDATED, USER_NAME, ROLE_NAME,
       LEFT(QUERY_TEXT,300) AS QUERY_TEXT_PREVIEW
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('DAY',-30,CURRENT_TIMESTAMP())
  AND QUERY_TEXT ILIKE '%CURATED_JSON%'
  AND QUERY_TYPE IN ('UPDATE','MERGE')
ORDER BY START_TIME DESC
LIMIT 100;
