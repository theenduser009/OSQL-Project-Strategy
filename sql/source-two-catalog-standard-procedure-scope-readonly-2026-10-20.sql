-- OSCAL Source Two / 2026-10-20 / READ ONLY / ONE RESULT TABLE
-- DECISION GATE: how many of 38,460 verified Control Standard -> Procedure
-- pairs are attached to Control Standards directly referenced by the existing
-- native Source Two Catalog four-level owner input?
--
-- This is only SCOPE ELIGIBILITY, not approved link.href, Catalog placement,
-- source/target OSCAL value QA, model conformance, PREVIEW, COMMIT or DIM readback.
-- Do not take a Source/Group -> Procedures cross-product. Each pair comes from
-- Control Standards (LevelId 41) CR field 30705, already parity-verified
-- against Control Procedures (LevelId 39) RR field 30704 in owner-run DEV.
-- Four direct source-level CONTROL_STANDARDS inputs exactly match the private
-- seven-cell Catalog native control assembler. Derived owner rollups excluded.
-- No actual ContentId, business fields, or hidden client values are returned.
-- No DDL/DML, no notebook state access, no registry/mapping/Catalog table writes.

WITH source_owner_refs AS (
    SELECT 'Source' AS SOURCE_LEVEL, s.CONTENT_ID AS OWNER_CONTENT_ID,
           f.VALUE AS STANDARD_MEMBER
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"CONTROL_STANDARDS") f
    UNION ALL
    SELECT 'Topic', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"CONTROL_STANDARDS") f
    UNION ALL
    SELECT 'Section', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"CONTROL_STANDARDS") f
    UNION ALL
    SELECT 'Sub-Section', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"CONTROL_STANDARDS") f
),
parsed_direct_refs AS (
    SELECT SOURCE_LEVEL, OWNER_CONTENT_ID,
           IFF(TYPEOF(STANDARD_MEMBER) = 'INTEGER'
                 AND TRY_TO_NUMBER(STANDARD_MEMBER::VARCHAR) > 0,
               TRY_TO_NUMBER(STANDARD_MEMBER::VARCHAR), NULL) AS STANDARD_ID
    FROM source_owner_refs
),
owner_standard AS (
    SELECT DISTINCT SOURCE_LEVEL, OWNER_CONTENT_ID, STANDARD_ID
    FROM parsed_direct_refs
    WHERE STANDARD_ID IS NOT NULL
),
standard_scope AS (
    SELECT DISTINCT STANDARD_ID FROM owner_standard
),
procedure_pairs AS (
    SELECT DISTINCT s.CONTENT_ID AS STANDARD_ID,
           TRY_TO_NUMBER(f.VALUE:"ContentId"::VARCHAR) AS PROCEDURE_ID
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_CONTROL_STANDARDS_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
    WHERE f.VALUE:"LevelId"::VARCHAR = '39'
      AND REGEXP_LIKE(f.VALUE:"ContentId"::VARCHAR, '^[1-9][0-9]*$')
),
owner_pairs AS (
    SELECT o.SOURCE_LEVEL, o.OWNER_CONTENT_ID,
           p.STANDARD_ID, p.PROCEDURE_ID
    FROM owner_standard o
    INNER JOIN procedure_pairs p ON p.STANDARD_ID = o.STANDARD_ID
),
pair_by_level AS (
    SELECT DISTINCT SOURCE_LEVEL, STANDARD_ID, PROCEDURE_ID
    FROM owner_pairs
),
all_scoped_pairs AS (
    SELECT DISTINCT STANDARD_ID, PROCEDURE_ID
    FROM owner_pairs
),
out_of_scope_pairs AS (
    SELECT p.STANDARD_ID, p.PROCEDURE_ID
    FROM procedure_pairs p
    LEFT JOIN standard_scope s ON p.STANDARD_ID = s.STANDARD_ID
    WHERE s.STANDARD_ID IS NULL
),
owner_level_stats AS (
    SELECT SOURCE_LEVEL,
           COUNT(*) AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
           COUNT_IF(STANDARD_ID IS NULL) AS INVALID_OR_NONINTEGER_REF_ITEMS,
           COUNT(DISTINCT STANDARD_ID) AS DISTINCT_DIRECT_STANDARD_IDS
    FROM parsed_direct_refs
    GROUP BY SOURCE_LEVEL
),
direct_pair_stats AS (
    SELECT SOURCE_LEVEL,
           COUNT(*) AS DISTINCT_STANDARD_PROCEDURE_PAIRS,
           COUNT(DISTINCT STANDARD_ID) AS STANDARDS_WITH_PROCEDURE_PAIRS,
           COUNT(DISTINCT PROCEDURE_ID) AS DISTINCT_PROCEDURE_IDS
    FROM pair_by_level
    GROUP BY SOURCE_LEVEL
),
owner_pair_stats AS (
    SELECT SOURCE_LEVEL,
           COUNT(*) AS OWNER_STANDARD_PROCEDURE_PAIR_INSTANCES
    FROM owner_pairs
    GROUP BY SOURCE_LEVEL
),
level_labels AS (
    SELECT column1::VARCHAR AS SOURCE_LEVEL
    FROM VALUES ('Source'), ('Topic'), ('Section'), ('Sub-Section')
),
by_level AS (
    SELECT l.SOURCE_LEVEL,
           COALESCE(o.DIRECT_STANDARD_REFERENCE_OCCURRENCES, 0) AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
           COALESCE(o.INVALID_OR_NONINTEGER_REF_ITEMS, 0) AS INVALID_OR_NONINTEGER_REF_ITEMS,
           COALESCE(o.DISTINCT_DIRECT_STANDARD_IDS, 0) AS DISTINCT_DIRECT_STANDARD_IDS,
           COALESCE(p.STANDARDS_WITH_PROCEDURE_PAIRS, 0) AS STANDARDS_WITH_PROCEDURE_PAIRS,
           COALESCE(p.DISTINCT_PROCEDURE_IDS, 0) AS DISTINCT_PROCEDURE_IDS,
           COALESCE(p.DISTINCT_STANDARD_PROCEDURE_PAIRS, 0) AS DISTINCT_STANDARD_PROCEDURE_PAIRS,
           COALESCE(i.OWNER_STANDARD_PROCEDURE_PAIR_INSTANCES, 0) AS OWNER_STANDARD_PROCEDURE_PAIR_INSTANCES
    FROM level_labels l
    LEFT JOIN owner_level_stats o ON o.SOURCE_LEVEL = l.SOURCE_LEVEL
    LEFT JOIN direct_pair_stats p ON p.SOURCE_LEVEL = l.SOURCE_LEVEL
    LEFT JOIN owner_pair_stats i ON i.SOURCE_LEVEL = l.SOURCE_LEVEL
),
all_scoped AS (
    SELECT 'ALL_SOURCE_TWO_DIRECT_OWNERS' AS SOURCE_LEVEL,
           (SELECT COUNT(*) FROM parsed_direct_refs) AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
           (SELECT COUNT_IF(STANDARD_ID IS NULL) FROM parsed_direct_refs) AS INVALID_OR_NONINTEGER_REF_ITEMS,
           (SELECT COUNT(*) FROM standard_scope) AS DISTINCT_DIRECT_STANDARD_IDS,
           (SELECT COUNT(DISTINCT STANDARD_ID) FROM all_scoped_pairs) AS STANDARDS_WITH_PROCEDURE_PAIRS,
           (SELECT COUNT(DISTINCT PROCEDURE_ID) FROM all_scoped_pairs) AS DISTINCT_PROCEDURE_IDS,
           (SELECT COUNT(*) FROM all_scoped_pairs) AS DISTINCT_STANDARD_PROCEDURE_PAIRS,
           (SELECT COUNT(*) FROM owner_pairs) AS OWNER_STANDARD_PROCEDURE_PAIR_INSTANCES
),
out_of_scope AS (
    SELECT 'OUTSIDE_SOURCE_TWO_DIRECT_OWNER_SCOPE' AS SOURCE_LEVEL,
           0 AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
           0 AS INVALID_OR_NONINTEGER_REF_ITEMS,
           0 AS DISTINCT_DIRECT_STANDARD_IDS,
           COUNT(DISTINCT STANDARD_ID) AS STANDARDS_WITH_PROCEDURE_PAIRS,
           COUNT(DISTINCT PROCEDURE_ID) AS DISTINCT_PROCEDURE_IDS,
           COUNT(*) AS DISTINCT_STANDARD_PROCEDURE_PAIRS,
           0 AS OWNER_STANDARD_PROCEDURE_PAIR_INSTANCES
    FROM out_of_scope_pairs
)
SELECT * FROM by_level
UNION ALL SELECT * FROM all_scoped
UNION ALL SELECT * FROM out_of_scope
ORDER BY
    CASE SOURCE_LEVEL
        WHEN 'Source' THEN 1 WHEN 'Topic' THEN 2
        WHEN 'Section' THEN 3 WHEN 'Sub-Section' THEN 4
        WHEN 'ALL_SOURCE_TWO_DIRECT_OWNERS' THEN 5
        ELSE 6 END;

-- Exactly six aggregate rows expected, regardless of whether any level is empty.
-- ALL_SCOPE distinct pair count + OUTSIDE_SCOPE distinct pair count should equal
-- full-RAW parity accepted count (38,460), if the RAW snapshot is unchanged.
-- The per-level rows may overlap and MUST NOT be summed as distinct pairs.
-- An individual Standard ID can have different ownership in different Catalogs;
-- "OWNER_*_PAIR_INSTANCES" is not an accepted final node/link count.
-- No native OSCAL links are approved by this scope check.
