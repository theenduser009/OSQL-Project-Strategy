-- OSCAL Source Two / 2026-10-20 / ONE READ-ONLY METADATA GATE.
-- Purpose: locate the actual stable Archer FIELD GUID for exactly the eight
-- Archer reference fields already identified by LevelId+FieldId.
-- The Oct 20 meeting's future custom prop.name rule uses the field's GUID,
-- NOT its numeric FIELD_ID or mutable SQL_FIELD_NAME. We must not invent a GUID.
-- The previous 303,983 owner references, 38,460 CR/RR pair parity, 38,311
-- Standard Procedure source scope, 10,422 persisted Catalog controls, and
-- five-row owner closure query are ALREADY verified; do not rerun those.
--
-- Reads only Archer metadata (8 field IDs). No RAW business values, source
-- ContentIds, current DIM/FACT, mapping CSV or notebook cells are touched.
-- Outputs only selected metadata field names and likely GUID/UUID columns.
-- Empty GUID_COLUMN_CANDIDATES means the actual GUID column is not available
-- with a recognizable name at this metadata level; it is NOT permission to
-- substitute FIELD_ID as a prop name.
--
-- Wildcard metadata object construction supports an unknown GUID column name
-- without dynamic SQL or assuming a specific private source schema.
WITH wanted AS (
    SELECT column1::VARCHAR AS REFERENCE_OWNER,
           column2::NUMBER  AS LEVEL_ID,
           column3::NUMBER  AS FIELD_ID
    FROM VALUES
       ('SOURCE',             6, 30706),
       ('TOPIC',              7, 30708),
       ('SECTION',            8, 30710),
       ('SUB_SECTION',        9, 30712),
       ('CONTROL_STANDARDS', 41, 30705),
       ('CONTROL_PROCEDURES',39, 30704),
       ('CONTROL_PROCEDURES',39, 3088),
       ('CONTROL_STANDARDS', 41, 2497)
),
meta AS (
    SELECT
        w.REFERENCE_OWNER, w.LEVEL_ID, w.FIELD_ID,
        m.SQL_FIELD_NAME,
        IFF(m.FIELD_ID IS NULL, 0, 1) AS META_FIELD_ID_MATCH,
        OBJECT_CONSTRUCT_KEEP_NULL(m.*) AS FULL_METADATA_RECORD
    FROM wanted w
    LEFT JOIN RTX_RAW_DEV.ES_ESC_GRC.ARCHER_META_FIELD m
      ON m.LEVEL_ID = w.LEVEL_ID
     AND m.FIELD_ID = w.FIELD_ID
),
guid_candidates AS (
    SELECT
        m.LEVEL_ID, m.FIELD_ID,
        k.KEY::VARCHAR AS CANDIDATE_COLUMN,
        IFF(IS_NULL_VALUE(k.VALUE), NULL, k.VALUE::VARCHAR) AS CANDIDATE_VALUE
    FROM meta m,
         LATERAL FLATTEN(INPUT => m.FULL_METADATA_RECORD) k
    WHERE UPPER(k.KEY::VARCHAR) LIKE '%GUID%'
       OR UPPER(k.KEY::VARCHAR) LIKE '%UUID%'
),
candidate_totals AS (
    SELECT
        LEVEL_ID, FIELD_ID,
        COUNT(*) AS CANDIDATE_COLUMN_COUNT,
        COUNT_IF(CANDIDATE_VALUE IS NOT NULL
                 AND LENGTH(TRIM(CANDIDATE_VALUE)) > 0) AS NONEMPTY_CANDIDATE_COUNT,
        LISTAGG(DISTINCT CANDIDATE_COLUMN, ', ')
          WITHIN GROUP (ORDER BY CANDIDATE_COLUMN) AS GUID_COLUMN_CANDIDATES,
        LISTAGG(
          CANDIDATE_COLUMN || '=' || COALESCE(CANDIDATE_VALUE, '<NULL>'), ' ; '
        ) WITHIN GROUP (ORDER BY CANDIDATE_COLUMN) AS GUID_VALUE_CANDIDATES
    FROM guid_candidates
    GROUP BY LEVEL_ID, FIELD_ID
)
SELECT
    m.REFERENCE_OWNER,
    m.LEVEL_ID,
    m.FIELD_ID,
    m.SQL_FIELD_NAME,
    m.META_FIELD_ID_MATCH,
    COALESCE(c.CANDIDATE_COLUMN_COUNT, 0) AS CANDIDATE_COLUMN_COUNT,
    COALESCE(c.NONEMPTY_CANDIDATE_COUNT, 0) AS NONEMPTY_CANDIDATE_COUNT,
    COALESCE(c.GUID_COLUMN_CANDIDATES, '') AS GUID_COLUMN_CANDIDATES,
    COALESCE(c.GUID_VALUE_CANDIDATES, '') AS GUID_VALUE_CANDIDATES
FROM meta m
LEFT JOIN candidate_totals c
  ON m.LEVEL_ID = c.LEVEL_ID AND m.FIELD_ID = c.FIELD_ID
ORDER BY
    CASE m.REFERENCE_OWNER
        WHEN 'SOURCE' THEN 1 WHEN 'TOPIC' THEN 2
        WHEN 'SECTION' THEN 3 WHEN 'SUB_SECTION' THEN 4
        WHEN 'CONTROL_STANDARDS' THEN 5 ELSE 6 END,
    m.FIELD_ID;

-- Expected 8 rows. Check every requested (LevelId,FieldId) identity:
--   - metadata row count should be exactly 1 (except already missing 41/2497)
--   - GUID values must be real stable Archer GUIDs, nonempty, and unique across
--     the seven populated distinct field IDs; this query does NOT prove
--     cross-environment stability, so any missing/ambiguous GUID is BLOCKED.
-- If no GUID/UUID-named column appears, do not guess or invent one:
-- an approved Archer metadata/raw schema source for GUIDs is still required.
-- Even populated GUIDs do not authorize a namespace; NIST OSCAL custom props
-- need an approved absolute URI ns. This is a mapping proposal, not COMMIT.
