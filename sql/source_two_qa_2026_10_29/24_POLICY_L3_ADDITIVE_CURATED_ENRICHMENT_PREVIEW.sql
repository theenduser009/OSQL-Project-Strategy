-- OSCAL Source Two | October 29, 2026 | READ-ONLY DESIGN PREVIEW
-- Preview an OPTIONAL additive Policy Level 3 lookup in CURATED_JSON.
-- Existing Matillion raw -> curated, UserList, ValuesListIds, GroupList,
-- pending-row guard, fallback, and original reference fields are UNCHANGED.
-- New proposed sidecar field: _OSCAL_POLICY_LEVEL3_RESOLUTIONS.
-- This query DOES NOT update the warehouse. It previews 5 owners per
-- Source/Topic/Section/Sub-Section, where a policy reference field exists.
-- Validated by owner: Policy Level3 RAW table, 13,278/13,278 matched refs,
-- split 10,929 structured objects and 2,349 Sub-Section scalar integers.
-- For actual future Matillion integration, build this as Stage 4 after
-- final_curated before the existing UPDATE output SELECT. DO NOT paste
-- this separate SELECT into an UPDATE as-is.
-- Explicitly preserve source field, array index and original reference.
-- An incomplete/ambiguous lookup skips the sidecar for that entire owner
-- (fail-safe), leaving the original CURATED_JSON byte-semantically intact.
-- Existing CURATED_JSON IS NULL rows are the only ones that the original
-- UPDATE processes. Historical non-null rows need a separate approved
-- additive-only backfill after full DEV preview/readback.
WITH sources AS (
    SELECT 'Source' AS SOURCE_LEVEL,
           'ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW' AS SOURCE_TABLE_NAME,
           CONTENT_ID::VARCHAR AS OWNER_CONTENT_ID,
           IFF(TYPEOF(CURATED_JSON) = 'VARCHAR',
               TRY_PARSE_JSON(CURATED_JSON::VARCHAR), CURATED_JSON) AS J
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW
    UNION ALL
    SELECT 'Topic', 'ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW',
           CONTENT_ID::VARCHAR,
           IFF(TYPEOF(CURATED_JSON) = 'VARCHAR',
               TRY_PARSE_JSON(CURATED_JSON::VARCHAR), CURATED_JSON)
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW
    UNION ALL
    SELECT 'Section', 'ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW',
           CONTENT_ID::VARCHAR,
           IFF(TYPEOF(CURATED_JSON) = 'VARCHAR',
               TRY_PARSE_JSON(CURATED_JSON::VARCHAR), CURATED_JSON)
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW
    UNION ALL
    SELECT 'Sub-Section', 'ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW',
           CONTENT_ID::VARCHAR,
           IFF(TYPEOF(CURATED_JSON) = 'VARCHAR',
               TRY_PARSE_JSON(CURATED_JSON::VARCHAR), CURATED_JSON)
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW
),
policy_fields AS (
    SELECT s.SOURCE_LEVEL, s.SOURCE_TABLE_NAME, s.OWNER_CONTENT_ID,
           f.KEY::VARCHAR AS SOURCE_FIELD_NAME, f.VALUE AS SOURCE_ARRAY
    FROM sources s,
         LATERAL FLATTEN(INPUT => IFF(TYPEOF(s.J) = 'OBJECT',
                                      s.J, OBJECT_CONSTRUCT())) f
    WHERE f.KEY IN (
        'POLICY_LEVEL_3',
        'POLICY_LEVEL_3_FROM_TOPIC_SECTION_AND_SUBSECTION_LEVELS',
        'POLICY_LEVEL_3_FROM_SECTION_AND_SUBSECTION_LEVELS',
        'POLICY_LEVEL_3_FROM_SECTION_LEVEL_AND_BELOW'
    )
      AND IS_ARRAY(f.VALUE)
      AND ARRAY_SIZE(f.VALUE) > 0
),
reference_items AS (
    SELECT p.SOURCE_LEVEL,p.SOURCE_TABLE_NAME,p.OWNER_CONTENT_ID,
           p.SOURCE_FIELD_NAME,
           f.INDEX AS SOURCE_ARRAY_INDEX,
           TYPEOF(f.VALUE) AS ORIGINAL_ITEM_TYPE,
           f.VALUE AS ORIGINAL_REFERENCE,
           CASE WHEN TYPEOF(f.VALUE)='OBJECT'
                THEN f.VALUE:ContentId::VARCHAR
                WHEN TYPEOF(f.VALUE) IN ('INTEGER','DECIMAL','VARCHAR')
                THEN f.VALUE::VARCHAR
                ELSE NULL END AS POLICY_CONTENT_ID,
           IFF(TYPEOF(f.VALUE)='OBJECT',
               f.VALUE:LevelId::VARCHAR,NULL) AS ORIGINAL_LEVEL_ID
    FROM policy_fields p,
         LATERAL FLATTEN(INPUT => p.SOURCE_ARRAY) f
),
targets AS (
    SELECT CONTENT_ID::VARCHAR AS POLICY_CONTENT_ID,
           COUNT(*) AS TARGET_MATCH_COUNT,
           COUNT_IF(CURATED_JSON IS NOT NULL) AS NONNULL_CURATED_ROWS,
           IFF(COUNT(*)=1,MAX(GET(CURATED_JSON,'POLICY_LEVEL_3_NAME')::VARCHAR),NULL)
             AS POLICY_NAME,
           IFF(COUNT(*)=1,MAX(GET(CURATED_JSON,'POLICY_NUMBER')::VARCHAR),NULL)
             AS POLICY_NUMBER
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_POLICIES_POLICY_LEVEL_3_RAW
    WHERE CONTENT_ID IS NOT NULL
    GROUP BY CONTENT_ID::VARCHAR
),
lookups AS (
    SELECT r.*,
           t.TARGET_MATCH_COUNT,
           CASE WHEN NOT REGEXP_LIKE(COALESCE(r.POLICY_CONTENT_ID,''),'^[1-9][0-9]*$')
                  THEN 'INVALID_CONTENT_ID'
                WHEN r.ORIGINAL_ITEM_TYPE='OBJECT'
                     AND r.ORIGINAL_LEVEL_ID IS DISTINCT FROM '5'
                  THEN 'OBJECT_LEVEL_NOT_5'
                WHEN r.ORIGINAL_ITEM_TYPE NOT IN ('OBJECT','INTEGER','DECIMAL','VARCHAR')
                  THEN 'UNSUPPORTED_ITEM_TYPE'
                WHEN t.POLICY_CONTENT_ID IS NULL THEN 'POLICY_TARGET_NOT_FOUND'
                WHEN t.TARGET_MATCH_COUNT <> 1 THEN 'DUPLICATE_TARGET_ID'
                WHEN t.NONNULL_CURATED_ROWS <> 1 THEN 'TARGET_JSON_MISSING'
                WHEN NULLIF(TRIM(t.POLICY_NAME),'') IS NULL THEN 'POLICY_NAME_MISSING'
                ELSE 'MATCHED' END AS LOOKUP_STATUS,
           IFF(t.TARGET_MATCH_COUNT=1,t.POLICY_NAME,NULL) AS POLICY_NAME,
           IFF(t.TARGET_MATCH_COUNT=1,t.POLICY_NUMBER,NULL) AS POLICY_NUMBER
    FROM reference_items r
    LEFT JOIN targets t ON t.POLICY_CONTENT_ID=r.POLICY_CONTENT_ID
),
per_field AS (
    SELECT SOURCE_LEVEL,SOURCE_TABLE_NAME,OWNER_CONTENT_ID,SOURCE_FIELD_NAME,
           COUNT(*) AS ITEM_COUNT,
           COUNT_IF(LOOKUP_STATUS <> 'MATCHED') AS ISSUE_COUNT,
           ARRAY_AGG(
             OBJECT_CONSTRUCT_KEEP_NULL(
               'ContractVersion','archer-policy-level3-resolved-v1',
               'SourceArrayIndex', SOURCE_ARRAY_INDEX,
               'OriginalItemType', ORIGINAL_ITEM_TYPE,
               'OriginalLevelId', ORIGINAL_LEVEL_ID,
               'ContentId', POLICY_CONTENT_ID,
               'ResolvedLevelId', 5,
               'PolicyName', POLICY_NAME,
               'PolicyNumber', POLICY_NUMBER,
               'ReferenceKind',
                   IFF(SOURCE_FIELD_NAME='POLICY_LEVEL_3','DIRECT','DESCENDANT_ROLLUP'),
               'LookupStatus',LOOKUP_STATUS
             )
           ) WITHIN GROUP (ORDER BY SOURCE_ARRAY_INDEX) AS RESOLVED_ITEMS
    FROM lookups
    GROUP BY SOURCE_LEVEL,SOURCE_TABLE_NAME,OWNER_CONTENT_ID,SOURCE_FIELD_NAME
),
per_owner AS (
    SELECT SOURCE_LEVEL,SOURCE_TABLE_NAME,OWNER_CONTENT_ID,
           SUM(ITEM_COUNT) AS REFERENCE_ITEMS,
           SUM(ISSUE_COUNT) AS ISSUE_COUNT,
           OBJECT_AGG(SOURCE_FIELD_NAME,TO_VARIANT(RESOLVED_ITEMS)) AS RESOLUTION_MAP
    FROM per_field
    GROUP BY SOURCE_LEVEL,SOURCE_TABLE_NAME,OWNER_CONTENT_ID
)
SELECT s.SOURCE_LEVEL,s.SOURCE_TABLE_NAME,s.OWNER_CONTENT_ID,
       o.REFERENCE_ITEMS,o.ISSUE_COUNT,
       CASE WHEN o.ISSUE_COUNT > 0 THEN 'FALLBACK_TO_ORIGINAL_JSON'
            WHEN ARRAY_CONTAINS(
                   TO_VARIANT('_OSCAL_POLICY_LEVEL3_RESOLUTIONS'),
                   OBJECT_KEYS(AS_OBJECT(s.J)))
               THEN 'SIDECAR_KEY_COLLISION_PRESERVE_ORIGINAL'
            ELSE 'ADDITIVE_PREVIEW_READY' END AS PREVIEW_STATUS,
       o.RESOLUTION_MAP AS RESOLVED_POLICY_REFERENCE_SIDECAR,
       CASE WHEN o.ISSUE_COUNT = 0
                 AND NOT ARRAY_CONTAINS(
                    TO_VARIANT('_OSCAL_POLICY_LEVEL3_RESOLUTIONS'),
                    OBJECT_KEYS(AS_OBJECT(s.J)))
            THEN OBJECT_INSERT(
                AS_OBJECT(s.J),
                '_OSCAL_POLICY_LEVEL3_RESOLUTIONS',
                TO_VARIANT(o.RESOLUTION_MAP),
                FALSE
            )
            ELSE AS_OBJECT(s.J)
       END AS ENRICHED_CURATED_JSON_PREVIEW
FROM sources s
JOIN per_owner o
  ON o.SOURCE_LEVEL=s.SOURCE_LEVEL
 AND o.SOURCE_TABLE_NAME=s.SOURCE_TABLE_NAME
 AND o.OWNER_CONTENT_ID=s.OWNER_CONTENT_ID
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY s.SOURCE_LEVEL ORDER BY s.OWNER_CONTENT_ID
) <= 5
ORDER BY s.SOURCE_LEVEL,s.OWNER_CONTENT_ID;
