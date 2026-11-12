-- Read-only Snowflake template. As shipped it runs on synthetic data.
-- For a live check, replace the input CTEs through catalog_controls with SELECTs
-- that expose the same columns. Set input_mode to LIVE after replacing them.
-- Use the field names, tables and source records from your own environment.
WITH settings (input_mode, control_level, reference_id_key, reference_level_key) AS (
    SELECT 'EXAMPLE', 'control', 'recordId', 'recordLevel'
), worksheet (worksheet_rows, worksheet_field, is_prefix, link_rel) AS (
    SELECT * FROM VALUES
        ('1', 'EXAMPLE_CONTROL_REFERENCE', FALSE, 'related'),
        ('2', 'EXAMPLE_SOURCE_URL', FALSE, 'source'),
        ('3', 'EXAMPLE_PREFIX_', TRUE, 'related')
), field_keys (field_key) AS (
    -- Use distinct curated JSON keys for the control record type.
    SELECT * FROM VALUES
        ('EXAMPLE_CONTROL_REFERENCE'), ('EXAMPLE_SOURCE_URL'), ('EXAMPLE_PREFIX_PARENT')
), control_records AS (
    -- Provide the source control record ID as text and its JSON as an OBJECT.
    SELECT column1 AS owner_id, AS_OBJECT(PARSE_JSON(column2)) AS doc
    FROM VALUES
        ('101', '{"EXAMPLE_CONTROL_REFERENCE":[{"recordId":102,"recordLevel":"control"},103,999],"EXAMPLE_SOURCE_URL":"https://example.org/controls/101","EXAMPLE_PREFIX_PARENT":102}'),
        ('102', '{"EXAMPLE_CONTROL_REFERENCE":[],"EXAMPLE_SOURCE_URL":null}')
), record_levels (target_id, target_level) AS (
    -- Provide reference record IDs and their levels as text.
    SELECT * FROM VALUES ('101', 'control'), ('102', 'control'), ('103', 'document')
), level_labels (target_level, level_name) AS (
    SELECT * FROM VALUES ('control', 'Control'), ('document', 'Document')
), catalog_controls (catalog_id, source_control_id) AS (
    -- Provide one row per saved control placement. Read the source control ID
    -- from the control's provenance property and use its owning Catalog ID.
    SELECT * FROM VALUES ('catalog-a', '101'), ('catalog-a', '102')
), resolved_fields AS (
    SELECT w.worksheet_rows, w.worksheet_field, w.link_rel,
           CASE WHEN NOT w.is_prefix THEN w.worksheet_field
                WHEN COUNT(DISTINCT k.field_key) = 1 THEN MIN(k.field_key) END AS source_field,
           ARRAY_AGG(DISTINCT k.field_key) WITHIN GROUP (ORDER BY k.field_key) AS metadata_candidates
    FROM worksheet w
    LEFT JOIN field_keys k ON IFF(w.is_prefix, STARTSWITH(k.field_key, w.worksheet_field),
                                  k.field_key = w.worksheet_field)
    GROUP BY w.worksheet_rows, w.worksheet_field, w.link_rel, w.is_prefix
), field_values AS (
    SELECT k.worksheet_rows, r.owner_id, GET(r.doc, k.source_field) AS source_value
    FROM resolved_fields k CROSS JOIN control_records r
    WHERE k.source_field IS NOT NULL
), nonempty AS (
    SELECT * FROM field_values
    WHERE source_value IS NOT NULL AND NOT IS_NULL_VALUE(source_value)
      AND COALESCE(TRIM(AS_VARCHAR(source_value)) <> '', TRUE)
      AND COALESCE(ARRAY_SIZE(AS_ARRAY(source_value)) > 0, TRUE)
      AND COALESCE(ARRAY_SIZE(OBJECT_KEYS(AS_OBJECT(source_value))) > 0, TRUE)
), source_counts AS (
    SELECT worksheet_rows, COUNT(DISTINCT owner_id) AS populated_controls,
           ARRAY_AGG(DISTINCT TYPEOF(source_value)) AS source_shapes
    FROM nonempty GROUP BY worksheet_rows
), member_values AS (
    SELECT n.worksheet_rows, n.owner_id, f.VALUE AS member
    FROM nonempty n, LATERAL FLATTEN(INPUT => IFF(IS_ARRAY(n.source_value), n.source_value,
                                                 ARRAY_CONSTRUCT(n.source_value)::VARIANT)) f
    WHERE f.VALUE IS NOT NULL AND NOT IS_NULL_VALUE(f.VALUE)
), parsed AS (
    SELECT m.worksheet_rows, m.owner_id,
           IFF(IS_OBJECT(m.member), GET_IGNORE_CASE(AS_OBJECT(m.member), s.reference_id_key)::VARCHAR,
               IFF(TYPEOF(m.member) IN ('INTEGER', 'VARCHAR'), m.member::VARCHAR, NULL)) AS id_candidate,
           GET_IGNORE_CASE(AS_OBJECT(m.member), s.reference_level_key)::VARCHAR AS declared_level,
           COALESCE(AS_VARCHAR(m.member),
                    AS_VARCHAR(GET_IGNORE_CASE(AS_OBJECT(m.member), 'href')),
                    AS_VARCHAR(GET_IGNORE_CASE(AS_OBJECT(m.member), 'url'))) AS url_candidate
    FROM member_values m CROSS JOIN settings s
), members AS (
    SELECT worksheet_rows, owner_id, declared_level,
           IFF(REGEXP_LIKE(TRIM(id_candidate), '[1-9][0-9]*'), TRIM(id_candidate), NULL) AS target_id,
           COALESCE(REGEXP_LIKE(TRIM(url_candidate), 'https?://[^[:space:]]+', 'i'), FALSE) AS has_http_url
    FROM parsed
), target_levels AS (
    SELECT r.target_id, MIN(r.target_level) AS target_level
    FROM record_levels r
    JOIN (SELECT DISTINCT target_id FROM members WHERE target_id IS NOT NULL) ids
      ON ids.target_id = r.target_id
    GROUP BY r.target_id
    HAVING COUNT(DISTINCT r.target_level) = 1
), verified AS (
    SELECT m.*, IFF(m.declared_level IS NULL OR m.declared_level = l.target_level,
                    l.target_level, NULL) AS verified_level
    FROM members m LEFT JOIN target_levels l ON l.target_id = m.target_id
), distinct_labels AS (
    SELECT target_level, MIN(level_name) AS level_name FROM level_labels GROUP BY target_level
), member_counts AS (
    SELECT v.worksheet_rows,
           COUNT_IF(v.has_http_url) AS http_url_members,
           COUNT_IF(v.target_id IS NOT NULL) AS record_reference_members,
           COUNT_IF(v.target_id IS NOT NULL AND v.verified_level IS NULL) AS unresolved_reference_members,
           COUNT_IF(NOT v.has_http_url AND v.target_id IS NULL) AS other_members,
           ARRAY_AGG(DISTINCT IFF(v.verified_level IS NULL, NULL,
               TRIM(v.verified_level || ' ' || COALESCE(l.level_name, '')))) AS resolved_target_levels
    FROM verified v LEFT JOIN distinct_labels l ON l.target_level = v.verified_level
    GROUP BY v.worksheet_rows
), same_catalog_pairs AS (
    -- These are candidate links. This query does not create OSCAL href values.
    SELECT DISTINCT v.worksheet_rows, v.owner_id, v.target_id
    FROM verified v
    JOIN catalog_controls src ON src.source_control_id = v.owner_id
    JOIN catalog_controls dst ON dst.source_control_id = v.target_id AND dst.catalog_id = src.catalog_id
    CROSS JOIN settings s
    WHERE v.verified_level = s.control_level AND v.owner_id <> v.target_id
), same_catalog_counts AS (
    SELECT worksheet_rows, COUNT(*) AS same_catalog_control_pairs
    FROM same_catalog_pairs GROUP BY worksheet_rows
)
SELECT p.input_mode, k.worksheet_rows, k.worksheet_field, k.source_field, k.link_rel, k.metadata_candidates,
       COALESCE(s.populated_controls, 0) AS populated_controls,
       COALESCE(s.source_shapes, ARRAY_CONSTRUCT()) AS source_shapes,
       COALESCE(m.http_url_members, 0) AS http_url_members,
       COALESCE(m.record_reference_members, 0) AS record_reference_members,
       COALESCE(m.unresolved_reference_members, 0) AS unresolved_reference_members,
       COALESCE(m.resolved_target_levels, ARRAY_CONSTRUCT()) AS resolved_target_levels,
       COALESCE(c.same_catalog_control_pairs, 0) AS same_catalog_control_pairs,
       COALESCE(m.other_members, 0) AS other_members
FROM resolved_fields k
LEFT JOIN source_counts s USING (worksheet_rows)
LEFT JOIN member_counts m USING (worksheet_rows)
LEFT JOIN same_catalog_counts c USING (worksheet_rows)
CROSS JOIN settings p
ORDER BY TRY_TO_NUMBER(SPLIT_PART(k.worksheet_rows, ',', 1));
