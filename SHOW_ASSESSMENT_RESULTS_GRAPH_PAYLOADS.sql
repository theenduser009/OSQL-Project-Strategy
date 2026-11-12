-- Run in a Snowflake worksheet with the schema containing the two OSCAL tables selected.
-- This read-only query picks one saved Assessment Results document with children.
-- Uncomment the two root filters to inspect a specific source record.
WITH RECURSIVE
elements AS (
    SELECT PK_DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT_HASH AS element_key,
           ELEMENT_TYPE, OSCAL_UUID, SOURCE_TABLE_NAME, SOURCE_RECORD_ID, METADATA_JSON
    FROM DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT
),
contains_edges AS (
    SELECT DISTINCT FK_SOURCE_ELEMENT_HASH AS parent_key,
                    FK_TARGET_ELEMENT_HASH AS child_key
    FROM FACT_OSCAL_ASSESSMENT_RESULTS_DEPENDENCY
    WHERE DEPENDENCY_TYPE = 'CONTAINS'
),
finding_owners AS (
    SELECT DISTINCT SOURCE_TABLE_NAME, SOURCE_RECORD_ID
    FROM elements
    WHERE ELEMENT_TYPE = 'findings'
),
root AS (
    SELECT e.element_key, e.ELEMENT_TYPE
    FROM elements e
    LEFT JOIN finding_owners f
      ON f.SOURCE_TABLE_NAME = e.SOURCE_TABLE_NAME
     AND f.SOURCE_RECORD_ID = e.SOURCE_RECORD_ID
    WHERE e.ELEMENT_TYPE = 'assessment-results'
      AND EXISTS (SELECT 1 FROM contains_edges d WHERE d.parent_key = e.element_key)
      -- AND e.SOURCE_TABLE_NAME = '<source table>'
      -- AND e.SOURCE_RECORD_ID = '<source record ID>'
    ORDER BY IFF(f.SOURCE_RECORD_ID IS NULL, 1, 0), e.element_key
    LIMIT 1
),
tree (element_key, parent_key, depth, hierarchy, key_path) AS (
    SELECT element_key,
           CAST(NULL AS BINARY(16)),
           0,
           CAST(ELEMENT_TYPE AS VARCHAR),
           CAST('/' || HEX_ENCODE(element_key) || '/' AS VARCHAR)
    FROM root

    UNION ALL

    SELECT c.element_key,
           d.parent_key,
           t.depth + 1,
           t.hierarchy || ' > ' || c.ELEMENT_TYPE,
           t.key_path || HEX_ENCODE(c.element_key) || '/'
    FROM tree t
    JOIN contains_edges d ON d.parent_key = t.element_key
    JOIN elements c ON c.element_key = d.child_key
    WHERE POSITION('/' || HEX_ENCODE(c.element_key) || '/', t.key_path) = 0
)
SELECT t.depth,
       t.hierarchy,
       HEX_ENCODE(t.element_key) AS element_id,
       HEX_ENCODE(t.parent_key) AS parent_element_id,
       e.ELEMENT_TYPE,
       e.OSCAL_UUID,
       e.SOURCE_TABLE_NAME,
       e.SOURCE_RECORD_ID,
       e.METADATA_JSON AS payload
FROM tree t
JOIN elements e ON e.element_key = t.element_key
ORDER BY t.key_path;
