-- OCT 29 2026: SQL 18, read-only Matillion / policy reference diagnostic.
-- Purpose: distinguish JSON array of numeric IDs from array of {ContentId,LevelId}
-- and check evidence of post-RAW field mapping and metadata enrichment.
-- THIS DOES NOT prove which particular Matillion UPDATE statement was deployed.
-- Repo code inspected: simplify-metadata-boundary @ c0fe30f030d2340b92199aeeb7ef42f2202ddd4a
-- Matillion candidate from 2026-10-01 only enriches UserList, ValuesListIds,
-- GroupList; it does not resolve policy record {ContentId,LevelId} into names.
-- Historical screenshots of a SELECT query are not proof UPDATE ran on all records.
--
-- Query 1: Rerun SQL 17 first, then execute this statement IMMEDIATELY.
-- SQL 17 returns POLICY_CONTENT_ID, ACTUAL_ARCHER_FIELD, FIELD_VALUE.
-- A plain numeric member can be a reference candidate, NOT a proven ContentId.
WITH prior AS (
 SELECT POLICY_CONTENT_ID::VARCHAR AS POLICY_CONTENT_ID,
        ACTUAL_ARCHER_FIELD::VARCHAR AS ARCHER_FIELD,
        FIELD_VALUE AS STORED_VALUE,
        COALESCE(TRY_PARSE_JSON(FIELD_VALUE::VARCHAR),FIELD_VALUE) AS PARSED_VALUE
 FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
), items AS (
 SELECT p.POLICY_CONTENT_ID, p.ARCHER_FIELD, p.STORED_VALUE,
        TYPEOF(p.PARSED_VALUE) AS PARSED_TYPE,
        x.INDEX AS MEMBER_INDEX, x.VALUE AS MEMBER,
        TYPEOF(x.VALUE) AS MEMBER_TYPE
 FROM prior p,
      LATERAL FLATTEN(INPUT=>IFF(IS_ARRAY(p.PARSED_VALUE),
                                  p.PARSED_VALUE,ARRAY_CONSTRUCT()),
                      OUTER=>TRUE) x
)
SELECT POLICY_CONTENT_ID, ARCHER_FIELD, PARSED_TYPE, MEMBER_INDEX,
       MEMBER_TYPE, MEMBER AS ORIGINAL_MEMBER,
       IFF(IS_OBJECT(MEMBER),MEMBER:ContentId::VARCHAR,NULL)
          AS OBJECT_CONTENT_ID,
       IFF(IS_OBJECT(MEMBER),MEMBER:LevelId::VARCHAR,NULL)
          AS OBJECT_LEVEL_ID,
       IFF(MEMBER_TYPE IN ('INTEGER','DECIMAL','VARCHAR'),
           MEMBER::VARCHAR,NULL) AS SCALAR_ID_CANDIDATE,
       CASE WHEN MEMBER_TYPE='OBJECT'
                  AND MEMBER:ContentId IS NOT NULL
                  AND MEMBER:LevelId IS NOT NULL
               THEN 'OBJECT_CONTENTID_LEVELID_UNRESOLVED'
            WHEN MEMBER_TYPE IN ('INTEGER','DECIMAL')
               THEN 'NUMERIC_ID_CANDIDATE_LEVEL_UNKNOWN'
            WHEN MEMBER_TYPE='VARCHAR' AND TRY_TO_NUMBER(MEMBER::VARCHAR) IS NOT NULL
               THEN 'NUMERIC_STRING_CANDIDATE_LEVEL_UNKNOWN'
            WHEN MEMBER IS NULL AND PARSED_TYPE='ARRAY'
               THEN 'EMPTY_ARRAY_OR_EMPTY_ITEM'
            WHEN MEMBER IS NULL THEN 'NOT_AN_ARRAY'
            ELSE 'OTHER_ITEM_SHAPE'
       END AS REFERENCE_CLASS
FROM items
ORDER BY POLICY_CONTENT_ID, ARCHER_FIELD, MEMBER_INDEX
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
       GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS'):ResolvedValues
          AS RESOLVED_SELECT_VALUES,
       GET(J,'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS'):ResolvedUser
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

-- Query 4: Optional execution evidence for recent UPDATEs, subject to the
-- Snowsight role's query-history visibility. Seven days only; no row != no run.
-- For older runs check Matillion job history and Snowflake account usage.
SELECT QUERY_ID, START_TIME, QUERY_TYPE, EXECUTION_STATUS, ROWS_UPDATED,
       LEFT(QUERY_TEXT,300) AS QUERY_TEXT_PREVIEW
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
  END_TIME_RANGE_START => DATEADD('DAY',-7,CURRENT_TIMESTAMP()),
  RESULT_LIMIT => 10000))
WHERE QUERY_TYPE='UPDATE'
  AND QUERY_TEXT ILIKE '%CURATED_JSON%'
ORDER BY START_TIME DESC
LIMIT 100;
