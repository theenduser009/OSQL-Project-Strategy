-- Source Two CATALOG | 2026-10-20 | READ ONLY mapping correctness gate.
-- Validate whether a Source/Topic/Section/Sub-Section record's explicit
-- RELATED_CONTROL_PROCEDURES refs match procedures implied by that record's
-- directly attached CONTROL_STANDARDS. These are DISTINCT Archer field families.
-- The prior accepted pair check: 38,460 Standard -> Procedure pairs, of which
-- 38,311 appear on Standards directly referenced anywhere in Source Two.
-- The previous persisted-control check: 10,422 native controls; 38,311
-- distinct global anchored pairs; 410,598 per-Catalog anchored associations.
-- A correct target identity does NOT establish owner-grain business equivalence.
-- Do not fan out all Standards' Procedures to an owner or vice versa.
--
-- Output: exactly five AGGREGATE rows (4 levels and ALL). Never output ContentIds,
-- business values, URLs, names, source payloads or per-record mismatch details.
-- NO DML/DDL, notebook cell changes, CSV changes, or DIM/FACT access.
WITH owner_standard_items AS (
    SELECT 'Source' AS SOURCE_LEVEL, s.CONTENT_ID AS OWNER_ID,
           f.VALUE AS ITEM
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
owner_procedure_items AS (
    SELECT 'Source' AS SOURCE_LEVEL, s.CONTENT_ID AS OWNER_ID,
           f.VALUE AS ITEM
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
    UNION ALL
    SELECT 'Topic', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
    UNION ALL
    SELECT 'Section', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
    UNION ALL
    SELECT 'Sub-Section', s.CONTENT_ID, f.VALUE
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
),
owner_direct_standards AS (
    SELECT DISTINCT SOURCE_LEVEL, OWNER_ID,
           TRY_TO_NUMBER(ITEM::VARCHAR) AS STANDARD_ID
    FROM owner_standard_items
    WHERE TYPEOF(ITEM) = 'INTEGER'
      AND REGEXP_LIKE(ITEM::VARCHAR,'^[1-9][0-9]*$')
),
owner_direct_procedures AS (
    SELECT DISTINCT SOURCE_LEVEL, OWNER_ID,
           TRY_TO_NUMBER(ITEM:"ContentId"::VARCHAR) AS PROCEDURE_ID
    FROM owner_procedure_items
    WHERE TYPEOF(ITEM) = 'OBJECT'
      AND ITEM:"LevelId"::VARCHAR = '39'
      AND REGEXP_LIKE(ITEM:"ContentId"::VARCHAR,'^[1-9][0-9]*$')
),
standard_direct_procedures AS (
    SELECT DISTINCT s.CONTENT_ID AS STANDARD_ID,
           TRY_TO_NUMBER(f.VALUE:"ContentId"::VARCHAR) AS PROCEDURE_ID
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_CONTROL_STANDARDS_RAW s,
         LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
    WHERE TYPEOF(f.VALUE) = 'OBJECT'
      AND f.VALUE:"LevelId"::VARCHAR = '39'
      AND REGEXP_LIKE(f.VALUE:"ContentId"::VARCHAR,'^[1-9][0-9]*$')
),
inferred_owner_procedures AS (
    SELECT DISTINCT o.SOURCE_LEVEL, o.OWNER_ID, p.PROCEDURE_ID
    FROM owner_direct_standards o
    JOIN standard_direct_procedures p ON p.STANDARD_ID = o.STANDARD_ID
),
pair_presence AS (
    SELECT SOURCE_LEVEL, OWNER_ID, PROCEDURE_ID,
           MAX(EXPLICIT_OWNER_REF) AS EXPLICIT_OWNER_REF,
           MAX(IMPLIED_FROM_STANDARD) AS IMPLIED_FROM_STANDARD
    FROM (
        SELECT SOURCE_LEVEL, OWNER_ID, PROCEDURE_ID,
               1 AS EXPLICIT_OWNER_REF, 0 AS IMPLIED_FROM_STANDARD
        FROM owner_direct_procedures
        UNION ALL
        SELECT SOURCE_LEVEL, OWNER_ID, PROCEDURE_ID,
               0 AS EXPLICIT_OWNER_REF, 1 AS IMPLIED_FROM_STANDARD
        FROM inferred_owner_procedures
    ) u
    GROUP BY SOURCE_LEVEL, OWNER_ID, PROCEDURE_ID
),
pair_rollup AS (
    SELECT COALESCE(SOURCE_LEVEL, 'ALL_SOURCE_TWO_LEVELS') AS SOURCE_LEVEL,
           COUNT_IF(EXPLICIT_OWNER_REF = 1) AS EXPLICIT_DISTINCT_OWNER_PROCEDURE_PAIRS,
           COUNT_IF(IMPLIED_FROM_STANDARD = 1) AS STANDARD_IMPLIED_DISTINCT_OWNER_PROCEDURE_PAIRS,
           COUNT_IF(EXPLICIT_OWNER_REF = 1 AND IMPLIED_FROM_STANDARD = 1)
             AS PAIRS_PRESENT_IN_BOTH,
           COUNT_IF(EXPLICIT_OWNER_REF = 1 AND IMPLIED_FROM_STANDARD = 0)
             AS PAIRS_ONLY_EXPLICIT_OWNER,
           COUNT_IF(EXPLICIT_OWNER_REF = 0 AND IMPLIED_FROM_STANDARD = 1)
             AS PAIRS_ONLY_STANDARD_IMPLIED,
           COUNT(DISTINCT IFF(EXPLICIT_OWNER_REF = 1 AND IMPLIED_FROM_STANDARD = 0,
                              OWNER_ID, NULL)) AS OWNERS_WITH_EXPLICIT_ONLY,
           COUNT(DISTINCT IFF(EXPLICIT_OWNER_REF = 0 AND IMPLIED_FROM_STANDARD = 1,
                              OWNER_ID, NULL)) AS OWNERS_WITH_IMPLIED_ONLY
    FROM pair_presence
    GROUP BY ROLLUP(SOURCE_LEVEL)
),
raw_procedure_rollup AS (
    SELECT COALESCE(SOURCE_LEVEL, 'ALL_SOURCE_TWO_LEVELS') AS SOURCE_LEVEL,
           COUNT(*) AS EXPLICIT_REFERENCE_OCCURRENCES,
           COUNT_IF(
               TYPEOF(ITEM) <> 'OBJECT'
               OR ITEM:"LevelId"::VARCHAR IS NULL
               OR ITEM:"LevelId"::VARCHAR <> '39'
               OR NOT REGEXP_LIKE(ITEM:"ContentId"::VARCHAR,'^[1-9][0-9]*$')
           ) AS INVALID_OR_WRONG_LEVEL_PROCEDURE_ITEMS
    FROM owner_procedure_items
    GROUP BY ROLLUP(SOURCE_LEVEL)
),
raw_standard_rollup AS (
    SELECT COALESCE(SOURCE_LEVEL, 'ALL_SOURCE_TWO_LEVELS') AS SOURCE_LEVEL,
           COUNT(*) AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
           COUNT_IF(
               TYPEOF(ITEM) <> 'INTEGER'
               OR NOT REGEXP_LIKE(ITEM::VARCHAR,'^[1-9][0-9]*$')
           ) AS INVALID_DIRECT_STANDARD_ITEMS
    FROM owner_standard_items
    GROUP BY ROLLUP(SOURCE_LEVEL)
)
SELECT p.SOURCE_LEVEL,
       COALESCE(s.DIRECT_STANDARD_REFERENCE_OCCURRENCES,0)
           AS DIRECT_STANDARD_REFERENCE_OCCURRENCES,
       COALESCE(s.INVALID_DIRECT_STANDARD_ITEMS,0)
           AS INVALID_DIRECT_STANDARD_ITEMS,
       COALESCE(r.EXPLICIT_REFERENCE_OCCURRENCES,0)
           AS EXPLICIT_PROCEDURE_REFERENCE_OCCURRENCES,
       COALESCE(r.INVALID_OR_WRONG_LEVEL_PROCEDURE_ITEMS,0)
           AS INVALID_OR_WRONG_LEVEL_PROCEDURE_ITEMS,
       p.EXPLICIT_DISTINCT_OWNER_PROCEDURE_PAIRS,
       p.STANDARD_IMPLIED_DISTINCT_OWNER_PROCEDURE_PAIRS,
       p.PAIRS_PRESENT_IN_BOTH,
       p.PAIRS_ONLY_EXPLICIT_OWNER,
       p.PAIRS_ONLY_STANDARD_IMPLIED,
       p.OWNERS_WITH_EXPLICIT_ONLY,
       p.OWNERS_WITH_IMPLIED_ONLY
FROM pair_rollup p
LEFT JOIN raw_procedure_rollup r ON p.SOURCE_LEVEL = r.SOURCE_LEVEL
LEFT JOIN raw_standard_rollup s ON p.SOURCE_LEVEL = s.SOURCE_LEVEL
ORDER BY CASE p.SOURCE_LEVEL
    WHEN 'Source' THEN 1 WHEN 'Topic' THEN 2
    WHEN 'Section' THEN 3 WHEN 'Sub-Section' THEN 4
    ELSE 5 END;

-- Interpret:
--   PAIRS_ONLY_EXPLICIT_OWNER  = Archer owner->Procedure relationship with
--                                no direct Standard->Procedure witness here.
--   PAIRS_ONLY_STANDARD_IMPLIED = Standard->Procedure pair absent from this
--                                Archer owner's explicit Procedure references.
--   Do NOT silently substitute either family for the other.
--   The ALL row is a total across distinct (level, owner, procedure) triples.
--   If both are nonzero, original workbook owner-level "control[].links" does
--   NOT mean "attach all procedures of each directly referenced Standard."
--   Even if sets match, business owner and true OSCAL payload placement
--   still require approval; this query does not make a COMMIT.
