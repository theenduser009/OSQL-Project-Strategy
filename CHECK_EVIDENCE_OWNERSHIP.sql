-- Read-only. A link counts only when both endpoints and their Archer levels are verified.
-- Output is aggregate only. Observation references do not establish ownership.
WITH scope (source_field, expected_level) AS (
    SELECT * FROM VALUES
        ('EVIDENCE_REPOSITORY', 310), ('EVIDENCE_REPOSITORY_SELECTED_CONTROL_STANDARDS', 310),
        ('OLD_EVIDENCE_REPOSITORY', 310), ('ISSUES', 62), ('ISSUES_CONTROL_STANDARD', 283)
), standards AS (
    SELECT CONTENT_ID::VARCHAR AS standard_id, TRY_PARSE_JSON(CURATED_JSON::VARCHAR) AS doc
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_CONTROL_STANDARDS_RAW
), standard_fields AS (
    SELECT s.standard_id, f.source_field, f.expected_level, GET(s.doc, f.source_field) AS refs
    FROM standards s CROSS JOIN scope f
), standard_refs AS (
    SELECT DISTINCT s.standard_id, s.source_field, s.expected_level,
           CASE WHEN IS_OBJECT(v.VALUE) THEN v.VALUE:ContentId::VARCHAR
                WHEN TYPEOF(v.VALUE) IN ('INTEGER', 'VARCHAR') THEN v.VALUE::VARCHAR END AS target_id,
           v.VALUE:LevelId::VARCHAR AS declared_level
    FROM standard_fields s,
         LATERAL FLATTEN(INPUT => IFF(IS_ARRAY(s.refs), s.refs, PARSE_JSON('[]'))) v
), wanted AS (
    SELECT DISTINCT expected_level, target_id
    FROM standard_refs WHERE REGEXP_LIKE(target_id, '[1-9][0-9]*')
), target_rows AS (
    SELECT 310 AS level_id, r.CONTENT_ID::VARCHAR AS target_id, TRY_PARSE_JSON(r.CURATED_JSON::VARCHAR) AS doc
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_EVIDENCE_REPOSITORY_RAW r
    JOIN wanted w ON w.expected_level = 310 AND w.target_id = r.CONTENT_ID::VARCHAR
    UNION ALL
    SELECT 62, r.CONTENT_ID::VARCHAR, TRY_PARSE_JSON(r.CURATED_JSON::VARCHAR)
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_FINDINGS_RAW r
    JOIN wanted w ON w.expected_level = 62 AND w.target_id = r.CONTENT_ID::VARCHAR
    UNION ALL
    SELECT 283, r.CONTENT_ID::VARCHAR, TRY_PARSE_JSON(r.CURATED_JSON::VARCHAR)
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_DEVIATIONS_RAW r
    JOIN wanted w ON w.expected_level = 283 AND w.target_id = r.CONTENT_ID::VARCHAR
), unique_docs AS (
    SELECT * FROM target_rows
    QUALIFY COUNT(*) OVER (PARTITION BY level_id, target_id) = 1
), reference_fields AS (
    SELECT LEVEL_ID, SQL_FIELD_NAME
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_FIELD
    WHERE LEVEL_ID IN (62, 283, 310)
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT FIELD_TYPE_ID) = 1 AND MAX(FIELD_TYPE_ID) IN (9, 23)
), doc_fields AS (
    SELECT d.level_id AS from_level, d.target_id AS from_id, k.KEY AS field_name, k.VALUE AS field_value
    FROM unique_docs d, LATERAL FLATTEN(INPUT => d.doc, MODE => 'OBJECT') k
), members AS (
    SELECT d.from_level, d.from_id, d.field_name,
           d.field_name || IFF(IS_ARRAY(d.field_value), '[]', '')
             || IFF(IS_OBJECT(v.VALUE), '.ContentId', '') AS field_path,
           CASE WHEN IS_OBJECT(v.VALUE) THEN v.VALUE:ContentId::VARCHAR
                WHEN TYPEOF(v.VALUE) IN ('INTEGER', 'VARCHAR') THEN v.VALUE::VARCHAR END AS to_id,
           v.VALUE:LevelId::VARCHAR AS declared_level
    FROM doc_fields d, LATERAL FLATTEN(
        INPUT => IFF(IS_ARRAY(d.field_value), d.field_value, ARRAY_CONSTRUCT_COMPACT(d.field_value)::VARIANT)
    ) v
), candidates AS (
    SELECT v.*
    FROM members v LEFT JOIN reference_fields f
      ON f.LEVEL_ID = v.from_level AND f.SQL_FIELD_NAME = v.field_name
    WHERE REGEXP_LIKE(v.to_id, '[1-9][0-9]*')
      AND (f.SQL_FIELD_NAME IS NOT NULL OR (REGEXP_LIKE(v.declared_level, '[1-9][0-9]*')
                                           AND ENDSWITH(v.field_path, '.ContentId')))
), metadata AS (
    SELECT CONTENT_ID::VARCHAR AS content_id, MIN(LEVEL_ID) AS level_id
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_CONTENT
    WHERE CONTENT_ID::VARCHAR IN (SELECT target_id FROM wanted UNION SELECT to_id FROM candidates)
    GROUP BY 1 HAVING COUNT(*) = 1
), standard_pairs AS (
    SELECT DISTINCT r.standard_id, r.source_field, r.expected_level, r.target_id, d.doc
    FROM standard_refs r
    JOIN metadata m ON m.content_id = r.target_id AND m.level_id = r.expected_level
    JOIN unique_docs d ON d.target_id = r.target_id AND d.level_id = r.expected_level
    WHERE IS_OBJECT(d.doc) AND (r.declared_level IS NULL OR r.declared_level = m.level_id::VARCHAR)
), edges AS (
    SELECT DISTINCT c.from_level, c.from_id, c.field_path, c.to_id, m.level_id AS to_level
    FROM candidates c JOIN metadata m ON m.content_id = c.to_id
    WHERE c.declared_level IS NULL OR c.declared_level = m.level_id::VARCHAR
), evidence AS (
    SELECT standard_id, source_field, target_id AS evidence_id,
           TYPEOF(doc:DESCRIPTION) = 'VARCHAR'
               AND NULLIF(TRIM(doc:DESCRIPTION::VARCHAR), '') IS NOT NULL AS has_description
    FROM standard_pairs WHERE expected_level = 310
), owners AS (
    SELECT standard_id, expected_level AS owner_level, target_id AS owner_id
    FROM standard_pairs WHERE expected_level IN (62, 283)
), same_standard_links AS (
    SELECT DISTINCT e.source_field, e.standard_id, e.evidence_id, o.owner_level, o.owner_id,
           'EVIDENCE_TO_OWNER' AS direction, x.field_path
    FROM evidence e
    JOIN edges x ON x.from_level = 310 AND x.from_id = e.evidence_id AND x.to_level IN (62, 283)
    JOIN owners o ON o.standard_id = e.standard_id AND o.owner_level = x.to_level AND o.owner_id = x.to_id
    UNION
    SELECT e.source_field, e.standard_id, e.evidence_id, o.owner_level, o.owner_id,
           'OWNER_TO_EVIDENCE', x.field_path
    FROM evidence e
    JOIN edges x ON x.to_level = 310 AND x.to_id = e.evidence_id AND x.from_level IN (62, 283)
    JOIN owners o ON o.standard_id = e.standard_id AND o.owner_level = x.from_level AND o.owner_id = x.from_id
), owner_links AS (
    SELECT source_field, standard_id, evidence_id, owner_level, owner_id,
           COUNT(DISTINCT direction) = 2 AS reciprocal
    FROM same_standard_links GROUP BY 1, 2, 3, 4, 5
), linked_pairs AS (
    SELECT source_field, standard_id, evidence_id, COUNT(*) AS owners,
           COUNT_IF(owner_level = 62) > 0 AS has_finding,
           COUNT_IF(owner_level = 283) > 0 AS has_deviation,
           COUNT_IF(reciprocal) > 0 AS has_reciprocal
    FROM owner_links GROUP BY 1, 2, 3
), counts AS (
    SELECT e.source_field, COUNT(DISTINCT e.standard_id) AS standards, COUNT(*) AS evidence_pairs,
           COUNT(DISTINCT e.evidence_id) AS evidence_records,
           COUNT(DISTINCT IFF(e.has_description, e.evidence_id, NULL)) AS evidence_records_with_description,
           COUNT_IF(e.has_description) AS pairs_with_description,
           COUNT_IF(l.has_finding) AS pairs_linked_to_finding,
           COUNT_IF(l.has_deviation) AS pairs_linked_to_deviation,
           COUNT_IF(l.has_reciprocal) AS pairs_linked_both_directions,
           COUNT_IF(l.owners > 1) AS pairs_with_multiple_owners
    FROM evidence e LEFT JOIN linked_pairs l
      ON l.source_field = e.source_field AND l.standard_id = e.standard_id AND l.evidence_id = e.evidence_id
    GROUP BY 1
), paths AS (
    SELECT source_field, ARRAY_AGG(DISTINCT direction || ' LEVEL ' || owner_level::VARCHAR || ' ' || field_path) AS owner_reference_paths
    FROM same_standard_links GROUP BY 1
), observation_paths AS (
    SELECT e.source_field, ARRAY_AGG(DISTINCT x.field_path || ' LEVEL ' || x.to_level::VARCHAR) AS evidence_to_observation_paths
    FROM evidence e JOIN edges x ON x.from_level = 310 AND x.from_id = e.evidence_id
    JOIN RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_LEVEL l ON l.LEVEL_ID = x.to_level
    WHERE l.MODULE_NAME ILIKE '%OBSERVATION%' OR l.LEVEL_NAME ILIKE '%OBSERVATION%'
    GROUP BY 1
)
SELECT f.source_field, COALESCE(c.standards, 0) AS standards, COALESCE(c.evidence_pairs, 0) AS evidence_pairs,
       COALESCE(c.evidence_records, 0) AS evidence_records,
       COALESCE(c.evidence_records_with_description, 0) AS evidence_records_with_description,
       COALESCE(c.pairs_with_description, 0) AS pairs_with_description,
       COALESCE(c.pairs_linked_to_finding, 0) AS pairs_linked_to_finding,
       COALESCE(c.pairs_linked_to_deviation, 0) AS pairs_linked_to_deviation,
       COALESCE(c.pairs_linked_both_directions, 0) AS pairs_linked_both_directions,
       COALESCE(c.pairs_with_multiple_owners, 0) AS pairs_with_multiple_owners,
       COALESCE(p.owner_reference_paths, ARRAY_CONSTRUCT()) AS owner_reference_paths,
       COALESCE(o.evidence_to_observation_paths, ARRAY_CONSTRUCT()) AS evidence_to_observation_paths
FROM scope f LEFT JOIN counts c ON c.source_field = f.source_field
LEFT JOIN paths p ON p.source_field = f.source_field
LEFT JOIN observation_paths o ON o.source_field = f.source_field
WHERE f.expected_level = 310
ORDER BY f.source_field;
