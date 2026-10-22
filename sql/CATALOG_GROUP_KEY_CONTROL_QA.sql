-- Source Two CATALOG | RELATED_TO_KEY_CONTROLS | READ-ONLY DEV QA | 2026-10-22
-- One SELECT, three count-only FIELD_SUMMARY rows: Topic, Section, Sub-Section.
-- This inspects the PERSISTED DIM, not an uncommitted notebook PREVIEW.
-- Existing direct scalar mapping: native embedded props[name='related-to-key-controls'].
-- No mapping activation, runtime-cell restart, DDL, DML, FACT join or COMMIT.
--
-- Storage contract: DIM has no ELEMENT_PATH. A group SOURCE_RECORD_ID is the
-- ROOT Source ID, never its original child ContentId. Identify depth using the
-- approved scoped native id and verify that its suffix equals the one canonical
-- STRING archer-content-id property. Do not join child CONTENT_ID to SOURCE_RECORD_ID.
-- This validates values at the declared group depth, not physical parent FACTs.
WITH levels AS (
  SELECT column1::NUMBER AS level_order, column2::VARCHAR AS source_level,
         column3::VARCHAR AS native_prefix
  FROM VALUES (1,'TOPIC','g-topics-'), (2,'SECTION','g-sections-'),
              (3,'SUB_SECTION','g-subsections-')
),
raw_rows AS (
  SELECT 'TOPIC' AS source_level, TO_VARCHAR(CONTENT_ID) AS child_id, CURATED_JSON AS doc
  FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW
  UNION ALL
  SELECT 'SECTION', TO_VARCHAR(CONTENT_ID), CURATED_JSON
  FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW
  UNION ALL
  SELECT 'SUB_SECTION', TO_VARCHAR(CONTENT_ID), CURATED_JSON
  FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW
),
raw_by_id AS (
  SELECT source_level,child_id,COUNT(*) AS raw_rows,
         COUNT(DISTINCT COALESCE(TO_JSON(doc),'<SQL_NULL>')) AS payload_versions,
         ANY_VALUE(doc) AS doc
  FROM raw_rows GROUP BY source_level,child_id
),
source_values AS (
  SELECT *, GET(doc,'RELATED_TO_KEY_CONTROLS') AS source_value,
         COALESCE(REGEXP_LIKE(child_id,'[1-9][0-9]*'),FALSE) AS identity_valid
  FROM raw_by_id
),
source_checks AS (
  SELECT *,
         doc IS NULL OR TYPEOF(doc)<>'OBJECT' AS document_invalid,
         source_value IS NULL OR IS_NULL_VALUE(source_value)
           OR (TYPEOF(source_value)='VARCHAR' AND source_value::VARCHAR='')
           OR (TYPEOF(source_value)='ARRAY' AND TO_JSON(source_value)='[]')
           OR (TYPEOF(source_value)='OBJECT' AND TO_JSON(source_value)='{}')
           AS source_unpopulated,
         ((COALESCE(TYPEOF(source_value) NOT IN
                    ('VARCHAR','INTEGER','DECIMAL','DOUBLE','BOOLEAN'),FALSE)
             AND NOT COALESCE(IS_NULL_VALUE(source_value),FALSE)
             AND NOT (TYPEOF(source_value)='ARRAY' AND TO_JSON(source_value)='[]')
             AND NOT (TYPEOF(source_value)='OBJECT' AND TO_JSON(source_value)='{}'))
           OR (TYPEOF(source_value) IN ('VARCHAR','DOUBLE')
             AND (TRIM(source_value::VARCHAR)='' AND source_value::VARCHAR<>''
               OR LOWER(TRIM(source_value::VARCHAR)) IN ('nan','inf','+inf','-inf'))))
           AS scalar_invalid,
         COALESCE(TYPEOF(source_value) IN ('DECIMAL','DOUBLE'),FALSE)
           AS numeric_rendering_review,
         CASE WHEN TYPEOF(source_value)='BOOLEAN' THEN LOWER(source_value::VARCHAR)
              WHEN TYPEOF(source_value) IN ('VARCHAR','INTEGER','DECIMAL','DOUBLE')
                THEN TRIM(source_value::VARCHAR)
         END AS expected_value
  FROM source_values
),
target_rows AS (
  SELECT ROW_NUMBER() OVER (
           ORDER BY SOURCE_RECORD_ID,TO_JSON(METADATA_JSON)
         ) AS target_row,
         SOURCE_RECORD_ID AS root_source_id,METADATA_JSON AS doc,
         GET(METADATA_JSON,'id') AS native_id,
         GET(METADATA_JSON,'props') AS props
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT
  WHERE UPPER(SOURCE_SYSTEM_NAME)='ARCHER'
    AND UPPER(SOURCE_TABLE_NAME)='ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW'
    AND LOWER(ELEMENT_TYPE)='groups'
),
target_props AS (
  SELECT t.target_row,ANY_VALUE(t.root_source_id) AS root_source_id,
         ANY_VALUE(t.doc) AS doc,ANY_VALUE(t.native_id) AS native_id,
         ANY_VALUE(t.props) AS props,
         SUM(IFF(p.value:name::VARCHAR='archer-content-id',1,0)) AS identity_props,
         MAX(IFF(p.value:name::VARCHAR='archer-content-id'
                   AND TYPEOF(p.value:value)='VARCHAR',p.value:value::VARCHAR,NULL))
           AS child_id,
         SUM(IFF(p.value:name::VARCHAR='related-to-key-controls',1,0)) AS value_props,
         SUM(IFF(p.value:name::VARCHAR='related-to-key-controls'
                   AND TYPEOF(p.value:value)='VARCHAR',1,0)) AS string_value_props,
         MAX(IFF(p.value:name::VARCHAR='related-to-key-controls'
                   AND TYPEOF(p.value:value)='VARCHAR',p.value:value::VARCHAR,NULL))
           AS target_value
  FROM target_rows t,
       LATERAL FLATTEN(INPUT=>IFF(TYPEOF(t.props)='ARRAY',t.props,ARRAY_CONSTRUCT()),
                       OUTER=>TRUE) p
  GROUP BY t.target_row
),
target_classified AS (
  SELECT p.*,l.source_level,l.native_prefix,
         COALESCE(TYPEOF(p.doc)='OBJECT'
           AND TYPEOF(p.native_id)='VARCHAR'
           AND TYPEOF(p.props)='ARRAY'
           AND p.identity_props=1
           AND REGEXP_LIKE(p.child_id,'[1-9][0-9]*')
           AND REGEXP_LIKE(p.root_source_id,'[1-9][0-9]*')
           AND p.native_id::VARCHAR=l.native_prefix||p.child_id,FALSE)
           AS identity_valid
  FROM target_props p LEFT JOIN levels l
    ON TYPEOF(p.native_id)='VARCHAR'
   AND STARTSWITH(p.native_id::VARCHAR,l.native_prefix)
),
target_by_id AS (
  SELECT source_level,child_id,COUNT(*) AS target_rows,
         SUM(IFF(value_props=0,1,0)) AS value_missing_rows,
         SUM(IFF(value_props>1,1,0)) AS value_duplicate_rows,
         SUM(IFF(value_props=1 AND string_value_props<>1,1,0)) AS value_wrong_type_rows,
         SUM(IFF(value_props=1 AND string_value_props=1
                   AND TRIM(target_value)='',1,0)) AS value_blank_rows,
         ANY_VALUE(target_value) AS target_value
  FROM target_classified WHERE identity_valid
  GROUP BY source_level,child_id
),
aligned AS (
  SELECT COALESCE(s.source_level,t.source_level) AS source_level,
         s.child_id IS NOT NULL AS source_exists,t.child_id IS NOT NULL AS target_exists,
         s.payload_versions,s.document_invalid,s.source_unpopulated,s.scalar_invalid,
         s.expected_value,s.numeric_rendering_review,t.target_rows,t.value_missing_rows,t.value_duplicate_rows,
         t.value_wrong_type_rows,t.value_blank_rows,t.target_value
  FROM (SELECT * FROM source_checks WHERE identity_valid) s
  FULL OUTER JOIN target_by_id t
    ON s.source_level=t.source_level AND s.child_id=t.child_id
),
level_counts AS (
  SELECT l.level_order,l.source_level,
         SUM(IFF(a.source_exists,1,0)) AS source_ids,
         SUM(IFF(a.target_exists,1,0)) AS persisted_target_ids,
         SUM(IFF(a.source_exists AND a.payload_versions=1 AND NOT a.document_invalid
                   AND NOT COALESCE(a.source_unpopulated,TRUE)
                   AND NOT a.scalar_invalid,1,0)) AS populated_source_ids,
         SUM(IFF(a.source_exists AND a.source_unpopulated,1,0)) AS source_without_value,
         SUM(IFF(a.source_exists AND a.payload_versions>1,1,0)) AS ambiguous_raw_ids,
         SUM(IFF(a.source_exists AND a.document_invalid,1,0)) AS invalid_source_document_ids,
         SUM(IFF(a.source_exists AND a.scalar_invalid,1,0)) AS invalid_source_value_ids,
         SUM(IFF(a.source_exists AND NOT a.target_exists,1,0)) AS missing_target_group_ids,
         SUM(IFF(a.target_exists AND a.target_rows>1,1,0)) AS duplicate_target_group_ids,
         SUM(IFF(a.source_exists AND a.payload_versions=1 AND NOT a.document_invalid
                   AND NOT COALESCE(a.source_unpopulated,TRUE) AND NOT a.scalar_invalid,
                   COALESCE(a.value_missing_rows,0),0)) AS missing_target_prop_rows,
         SUM(IFF(a.source_exists AND a.payload_versions=1 AND NOT a.document_invalid
                   AND a.source_unpopulated AND a.target_exists
                   AND a.value_missing_rows<a.target_rows,1,0))
           AS unexpected_prop_for_empty_source_ids,
         SUM(IFF(a.source_exists AND a.numeric_rendering_review,1,0))
           AS numeric_rendering_review_ids,
         SUM(COALESCE(a.value_duplicate_rows,0)) AS duplicate_target_prop_rows,
         SUM(COALESCE(a.value_wrong_type_rows,0)) AS wrong_target_prop_type_rows,
         SUM(COALESCE(a.value_blank_rows,0)) AS blank_target_prop_rows,
         SUM(IFF(a.source_exists AND a.payload_versions=1 AND NOT a.document_invalid
                   AND NOT COALESCE(a.source_unpopulated,TRUE) AND NOT a.scalar_invalid
                   AND a.target_rows=1 AND a.value_missing_rows=0
                   AND a.value_duplicate_rows=0 AND a.value_wrong_type_rows=0
                   AND a.value_blank_rows=0 AND NOT a.numeric_rendering_review AND a.expected_value=a.target_value,1,0))
           AS exact_matches,
         SUM(IFF(a.source_exists AND a.payload_versions=1 AND NOT a.document_invalid
                   AND NOT COALESCE(a.source_unpopulated,TRUE) AND NOT a.scalar_invalid
                   AND a.target_rows=1 AND a.value_missing_rows=0
                   AND a.value_duplicate_rows=0 AND a.value_wrong_type_rows=0
                   AND a.value_blank_rows=0 AND NOT a.numeric_rendering_review AND a.expected_value<>a.target_value,1,0))
           AS wrong_target_value_ids,
         SUM(IFF(a.target_exists AND NOT a.source_exists,1,0)) AS target_only_ids
  FROM levels l LEFT JOIN aligned a ON a.source_level=l.source_level
  GROUP BY l.level_order,l.source_level
),
raw_identity_counts AS (
  SELECT source_level,SUM(IFF(NOT identity_valid,raw_rows,0)) AS invalid_raw_identity_rows
  FROM source_checks GROUP BY source_level
),
target_identity_counts AS (
  SELECT source_level,SUM(IFF(NOT identity_valid,1,0)) AS invalid_target_identity_rows
  FROM target_classified GROUP BY source_level
),
global_identity_counts AS (
  SELECT COALESCE(SUM(IFF(NOT identity_valid,1,0)),0) AS global_invalid_target_identity_rows,
         COALESCE(SUM(IFF(source_level IS NULL,1,0)),0) AS unknown_target_group_depth_rows
  FROM target_classified
)
SELECT 'FIELD_SUMMARY' AS row_type,c.source_level,
       'RELATED_TO_KEY_CONTROLS' AS source_field,
       'props[related-to-key-controls].value' AS target_member,
       c.source_ids,c.persisted_target_ids,c.populated_source_ids,c.exact_matches,
       c.source_without_value,c.ambiguous_raw_ids,
       COALESCE(r.invalid_raw_identity_rows,0) AS invalid_raw_identity_rows,
       c.invalid_source_document_ids,c.invalid_source_value_ids,
       c.missing_target_group_ids,c.duplicate_target_group_ids,
       c.missing_target_prop_rows,c.unexpected_prop_for_empty_source_ids,
       c.numeric_rendering_review_ids,c.duplicate_target_prop_rows,
       c.wrong_target_prop_type_rows,c.blank_target_prop_rows,c.wrong_target_value_ids,
       c.target_only_ids,
       COALESCE(t.invalid_target_identity_rows,0) AS invalid_target_identity_rows_at_depth,
       g.global_invalid_target_identity_rows,g.unknown_target_group_depth_rows
FROM level_counts c
LEFT JOIN raw_identity_counts r ON r.source_level=c.source_level
LEFT JOIN target_identity_counts t ON t.source_level=c.source_level
CROSS JOIN global_identity_counts g
ORDER BY c.level_order;

-- Interpret populated values separately from unpopulated source data; null or
-- absent data is NOT a successful mapping test. Zero is populated and compares
-- with the native STRING "0". Property errors/duplicate groups count regardless
-- of source population. Global invalid-identity columns repeat in all three rows.
-- INTEGER zero is preserved. DECIMAL/DOUBLE values are counted separately as
-- NUMERIC_RENDERING_REVIEW_IDS and are excluded from EXACT_MATCHES and value
-- mismatches until Snowflake rendering is reconciled with Python/Decimal str().
-- Missing properties count only when populated source requires them; properties
-- unexpectedly present for empty source are reported separately.
-- Unknown/invalid target identity rows cannot be safely attributed to a child;
-- they remain explicit exceptions, never disappear in FLATTEN or count as PASS.
-- RAW duplicate payloads are unresolved; no invented "latest" ordering.
-- Existing DIM may represent an older release than current RAW or the 104-row
-- PREVIEW. A missing prop is not proof that the uncommitted candidate failed.
-- This query does not prove actual parent links, native controls, complete
-- document conformance, or COMMIT of the separate 104-row candidate.
