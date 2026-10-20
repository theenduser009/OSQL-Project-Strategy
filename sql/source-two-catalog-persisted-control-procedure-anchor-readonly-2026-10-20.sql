-- OSCAL Source Two / Snowflake DEV / 2026-10-20 / READ ONLY.
-- PURPOSE: count verified Standard -> Procedure pairs actually anchored to
-- persisted native Catalog control DIM nodes (not to each owner occurrence).
-- Previously owner-confirmed (different read-only query):
--  38,460 CR30705<->RR30704 pairs globally; 38,311 within four-level
--  direct-owner Source Two scope; 149 outside. This is the NEXT target-path gate.
-- Native Catalog control identity in current private Cell 4:
--  one control DIM node per (Catalog root ContentId, Standard ContentId),
--  unchanged by group/root LCA promotions; source ID in props 'archer-content-id'.
-- The 1,974,800 source owner association occurrences must NOT become links.
-- Existing DIM read-back does NOT prove that the 104-row new mapping committed.
--
-- This is a SELECT only. No private document text/ContentId is output.
-- Do not run mapper Cells 1-7, COMMIT, DDL/DML, update a CSV or generate href.
-- All numeric source IDs are checked and normalized only for matching.
-- A zero-count result requires reviewing ELEMENT_TYPE/metadata schema, not
-- automatically claiming no existing control nodes.

WITH native_control_nodes AS (
  SELECT
      c.PK_DIM_OSCAL_CATALOG_ELEMENT_HASH AS CONTROL_KEY,
      c.SOURCE_RECORD_ID::VARCHAR AS CATALOG_ROOT_ID,
      TRY_PARSE_JSON(TO_VARCHAR(c.METADATA_JSON)) AS CONTROL_JSON
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_CATALOG_ELEMENT c
  WHERE c.ELEMENT_TYPE = 'controls'
),
control_prop_profiles AS (
  SELECT
      n.CONTROL_KEY, n.CATALOG_ROOT_ID,
      MAX(IFF(n.CONTROL_JSON IS NULL, 1, 0)) AS BAD_CONTROL_PAYLOAD,
      SUM(IFF(f.VALUE:"name"::VARCHAR = 'archer-content-id', 1, 0))
          AS CONTENT_ID_PROPERTY_COUNT,
      MAX(IFF(f.VALUE:"name"::VARCHAR = 'archer-content-id',
              f.VALUE:"value"::VARCHAR, NULL)) AS STANDARD_ID_TEXT,
      MAX(IFF(n.CONTROL_JSON:"id" IS NULL
              OR n.CONTROL_JSON:"title" IS NULL, 1, 0))
          AS ID_OR_TITLE_MISSING,
      MAX(IFF(COALESCE(ARRAY_SIZE(n.CONTROL_JSON:"links"),0) > 0,1,0))
          AS EXISTING_CONTROL_LINKS_PRESENT
  FROM native_control_nodes n,
       LATERAL FLATTEN(INPUT => n.CONTROL_JSON:"props", OUTER => TRUE) f
  GROUP BY n.CONTROL_KEY, n.CATALOG_ROOT_ID
),
normalized_controls AS (
  SELECT *,
      IFF(
        CONTENT_ID_PROPERTY_COUNT = 1
        AND REGEXP_LIKE(STANDARD_ID_TEXT,'^[1-9][0-9]*$'),
        TRY_TO_NUMBER(STANDARD_ID_TEXT), NULL
      ) AS CONTROL_STANDARD_ID
  FROM control_prop_profiles
),
valid_controls AS (
  SELECT CONTROL_KEY, CATALOG_ROOT_ID, CONTROL_STANDARD_ID
  FROM normalized_controls
  WHERE CONTROL_STANDARD_ID IS NOT NULL
    AND BAD_CONTROL_PAYLOAD = 0
    AND ID_OR_TITLE_MISSING = 0
),
duplicate_logical_keys AS (
  SELECT CATALOG_ROOT_ID, CONTROL_STANDARD_ID, COUNT(*) AS NODES_PER_KEY
  FROM valid_controls
  GROUP BY CATALOG_ROOT_ID, CONTROL_STANDARD_ID
  HAVING COUNT(*) > 1
),
standard_procedure_pairs AS (
  SELECT DISTINCT
      s.CONTENT_ID AS CONTROL_STANDARD_ID,
      TRY_TO_NUMBER(f.VALUE:"ContentId"::VARCHAR) AS PROCEDURE_ID
  FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_CONTROL_STANDARDS_RAW s,
       LATERAL FLATTEN(INPUT => s.CURATED_JSON:"RELATED_CONTROL_PROCEDURES") f
  WHERE f.VALUE:"LevelId"::VARCHAR = '39'
    AND REGEXP_LIKE(f.VALUE:"ContentId"::VARCHAR, '^[1-9][0-9]*$')
),
native_node_procedure_pairs AS (
  SELECT
      n.CONTROL_KEY, n.CATALOG_ROOT_ID, n.CONTROL_STANDARD_ID, p.PROCEDURE_ID
  FROM valid_controls n
  JOIN standard_procedure_pairs p
    ON n.CONTROL_STANDARD_ID = p.CONTROL_STANDARD_ID
),
logical_node_procedure_pairs AS (
  SELECT DISTINCT CATALOG_ROOT_ID, CONTROL_STANDARD_ID, PROCEDURE_ID
  FROM native_node_procedure_pairs
),
global_matched_pairs AS (
  SELECT DISTINCT CONTROL_STANDARD_ID, PROCEDURE_ID
  FROM logical_node_procedure_pairs
),
native_control_counts AS (
  SELECT
    COUNT(*) AS PHYSICAL_NATIVE_CONTROL_NODES,
    COUNT_IF(BAD_CONTROL_PAYLOAD = 1) AS BAD_CONTROL_PAYLOAD_NODES,
    COUNT_IF(CONTENT_ID_PROPERTY_COUNT <> 1) AS CONTROL_CONTENT_ID_PROP_NOT_SINGLE,
    COUNT_IF(CONTENT_ID_PROPERTY_COUNT = 1 AND CONTROL_STANDARD_ID IS NULL)
      AS CONTROL_CONTENT_ID_NOT_POSITIVE_INTEGER,
    COUNT_IF(ID_OR_TITLE_MISSING = 1) AS CONTROL_ID_OR_TITLE_MISSING_NODES,
    COUNT_IF(EXISTING_CONTROL_LINKS_PRESENT = 1) AS CONTROLS_ALREADY_WITH_LINKS
  FROM normalized_controls
),
verified_anchors AS (
  SELECT
    COUNT(*) AS CONTROL_NODE_PROCEDURE_PAIR_INSTANCES,
    COUNT(DISTINCT CONTROL_KEY) AS CONTROL_NODES_WITH_PROCEDURES,
    COUNT(DISTINCT CATALOG_ROOT_ID) AS CATALOG_ROOTS_WITH_PROCEDURE_PAIRS,
    COUNT(DISTINCT CONTROL_STANDARD_ID) AS CONTROL_STANDARD_IDS_WITH_PROCEDURES,
    COUNT(DISTINCT PROCEDURE_ID) AS DISTINCT_PROCEDURE_IDS_WITH_ANCHORS
  FROM native_node_procedure_pairs
)
SELECT
  (SELECT COUNT(*) FROM native_control_nodes) AS NATIVE_CONTROL_NODES_READ,
  (SELECT PHYSICAL_NATIVE_CONTROL_NODES FROM native_control_counts)
    AS PHYSICAL_NATIVE_CONTROL_NODES,
  (SELECT BAD_CONTROL_PAYLOAD_NODES FROM native_control_counts)
    AS BAD_CONTROL_PAYLOAD_NODES,
  (SELECT CONTROL_CONTENT_ID_PROP_NOT_SINGLE FROM native_control_counts)
    AS CONTROL_CONTENT_ID_PROP_NOT_SINGLE,
  (SELECT CONTROL_CONTENT_ID_NOT_POSITIVE_INTEGER FROM native_control_counts)
    AS CONTROL_CONTENT_ID_NOT_POSITIVE_INTEGER,
  (SELECT CONTROL_ID_OR_TITLE_MISSING_NODES FROM native_control_counts)
    AS CONTROL_ID_OR_TITLE_MISSING_NODES,
  (SELECT CONTROLS_ALREADY_WITH_LINKS FROM native_control_counts)
    AS CONTROLS_ALREADY_WITH_LINKS,
  (SELECT COUNT(*) FROM duplicate_logical_keys)
    AS DUPLICATE_CATALOG_STANDARD_KEYS,
  (SELECT COUNT(*) FROM global_matched_pairs)
    AS VERIFIED_GLOBAL_STANDARD_PROCEDURE_PAIRS_IN_PERSISTED_CONTROLS,
  (SELECT COUNT(*) FROM logical_node_procedure_pairs)
    AS DISTINCT_CATALOG_STANDARD_PROCEDURE_ASSOCIATIONS,
  (SELECT CONTROL_NODE_PROCEDURE_PAIR_INSTANCES FROM verified_anchors)
    AS PHYSICAL_CONTROL_NODE_PROCEDURE_PAIR_INSTANCES,
  (SELECT CONTROL_NODES_WITH_PROCEDURES FROM verified_anchors)
    AS CONTROL_NODES_WITH_PROCEDURES,
  (SELECT CATALOG_ROOTS_WITH_PROCEDURE_PAIRS FROM verified_anchors)
    AS CATALOG_ROOTS_WITH_PROCEDURE_PAIRS,
  (SELECT CONTROL_STANDARD_IDS_WITH_PROCEDURES FROM verified_anchors)
    AS CONTROL_STANDARD_IDS_WITH_PROCEDURES,
  (SELECT DISTINCT_PROCEDURE_IDS_WITH_ANCHORS FROM verified_anchors)
    AS DISTINCT_PROCEDURE_IDS_WITH_ANCHORS;

-- Expected ONE summary row; screenshot horizontally to the last column.
-- This does not prove a new link or an updated 104-row committed release.
-- The global distinct anchored pair count should not exceed 38,311 unless
-- the RAW snapshot, Catalog control selection, or assumptions changed.
-- A control may appear in multiple Catalog roots: distinct Catalog-scoped
-- associations can exceed 38,311 while distinct GLOBAL pairs cannot.
-- Do not emit any 'link.href' without a real resource URI or a valid Back
-- Matter resource with actual rlink/base64 content and approved semantics.
