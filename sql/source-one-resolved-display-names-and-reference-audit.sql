-- SOURCE ONE / ARCHER AUTHORIZATION PACKAGE — HUMAN-READABLE OSCAL VIEW INPUTS
-- Prepared 2026-10-15. SELECT-ONLY. No DDL, DML, target reload, or COMMIT.
-- Source One mapping checked against the maintained CSV on
--   work/source-one-tbd-props-2026-10-15 (private project repository).
-- This public file has no actual Archer records, person names, or company data.
--
-- READ THIS BEFORE USING IN A CLIENT VIEW:
-- Query 1: readable names already available IN PERSISTED OSCAL:
--          all SSP responsible-party roles + any SSP system-characteristics
--          props containing a resolvable Curated UserList/ResolvedUser.
-- Query 2: cross-record Archer references awaiting a VERIFIED lookup.
--          Names are deliberately NULL until a LevelId/ContentId target is found.
-- Query 3: other source-one reference properties requiring resolution.
-- Query 4: discover candidate Archer lookup tables by name, read-only.
-- Query 5: discover their physical column names, read-only.
-- Query 6: POAM graph references (OSCAL UUID, not an Archer ContentId).
--
-- None of these queries treats a match of ContentId alone as a verified entity
-- name; target LevelId and correct owning app / row must be established first.
-- The last reported Source One SSP COMMIT was not verified; check actual
-- persisted values before claiming this output is complete.

-- ========================================================================
-- QUERY 1 — ALL AVAILABLE PERSON DISPLAY NAMES (ONE ROW PER ROLE/USER)
-- Role relationships come from metadata -> responsible-parties -> parties.
-- Additional UserList-based admin values are decoded from named SSP props.
-- No source RAW join; return only user-friendly name and context.
-- ========================================================================
WITH
role_nodes AS (
  SELECT a.SOURCE_RECORD_ID AS CONTENT_ID,
         a.METADATA_JSON:"role-id"::STRING AS ROLE_ID,
         a.METADATA_JSON:"party-uuids" AS PARTY_UUIDS
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT a
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY e
    ON e.FK_TARGET_ELEMENT_HASH = a.PK_OSCAL_SSP_ELEMENT_HASH
   AND e.DEPENDENCY_TYPE = 'CONTAINS'
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT m
    ON m.PK_OSCAL_SSP_ELEMENT_HASH = e.FK_SOURCE_ELEMENT_HASH
   AND m.SOURCE_RECORD_ID = a.SOURCE_RECORD_ID
   AND m.ELEMENT_TYPE = 'metadata'
  WHERE a.ELEMENT_TYPE = 'responsible-parties'
    AND a.SOURCE_SYSTEM_NAME = 'ARCHER'
    AND a.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
),
role_members AS (
  SELECT n.CONTENT_ID, n.ROLE_ID, f.VALUE::STRING AS PARTY_UUID
  FROM role_nodes n, LATERAL FLATTEN(INPUT => n.PARTY_UUIDS) f
),
party_nodes AS (
  SELECT SOURCE_RECORD_ID AS CONTENT_ID, METADATA_JSON AS PARTY_JSON
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
  WHERE ELEMENT_TYPE = 'parties'
    AND SOURCE_SYSTEM_NAME = 'ARCHER'
    AND SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
),
role_names AS (
  SELECT rm.CONTENT_ID,
         rm.ROLE_ID AS ROLE_OR_ARCHER_FIELD,
         NULLIF(TRIM(p.PARTY_JSON:"name"::STRING),'') AS DISPLAY_NAME,
         IFF(NULLIF(TRIM(p.PARTY_JSON:"name"::STRING),'') IS NULL,
             'NAME_NOT_AVAILABLE_IN_PARTY',
             'RESOLVED_FROM_OSCAL_PARTY') AS RESOLUTION_STATUS
  FROM role_members rm
  LEFT JOIN party_nodes p
    ON p.CONTENT_ID = rm.CONTENT_ID
   AND REPLACE(p.PARTY_JSON:"uuid"::STRING,'-','') =
       REPLACE(rm.PARTY_UUID,'-','')
),
ssp_properties AS (
  SELECT p.SOURCE_RECORD_ID AS CONTENT_ID,
         p.METADATA_JSON:"name"::STRING AS PROPERTY_NAME,
         p.METADATA_JSON:"value"::STRING AS PROPERTY_TEXT
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT p
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY e
    ON e.FK_TARGET_ELEMENT_HASH = p.PK_OSCAL_SSP_ELEMENT_HASH
   AND e.DEPENDENCY_TYPE = 'CONTAINS'
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT sc
    ON sc.PK_OSCAL_SSP_ELEMENT_HASH = e.FK_SOURCE_ELEMENT_HASH
   AND sc.ELEMENT_TYPE = 'system-characteristics'
   AND sc.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID
  WHERE p.ELEMENT_TYPE = 'props'
    AND p.SOURCE_SYSTEM_NAME = 'ARCHER'
    AND p.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
),
parsed_props AS (
  SELECT CONTENT_ID, PROPERTY_NAME,
         TRY_PARSE_JSON(PROPERTY_TEXT) AS SOURCE_REFERENCE
  FROM ssp_properties
),
user_members AS (
  SELECT p.CONTENT_ID, p.PROPERTY_NAME,
         u.VALUE:"ResolvedUser" AS PERSON,
         u.VALUE:"Id"::STRING AS ARCHER_USER_ID
  FROM parsed_props p,
       LATERAL FLATTEN(INPUT => p.SOURCE_REFERENCE:"UserList") u
),
user_names AS (
  SELECT CONTENT_ID,
         UPPER(REPLACE(PROPERTY_NAME,'-','_')) AS ROLE_OR_ARCHER_FIELD,
         NULLIF(TRIM(ARRAY_TO_STRING(
             ARRAY_CONSTRUCT_COMPACT(
               NULLIF(TRIM(PERSON:"FIRST_NAME"::STRING),''),
               NULLIF(TRIM(PERSON:"MIDDLE_NAME"::STRING),''),
               NULLIF(TRIM(PERSON:"LAST_NAME"::STRING),'')
             ), ' ')), '') AS DISPLAY_NAME,
         IFF(PERSON:"LookupStatus"::STRING IN ('MATCHED','MATCHED_MISSING_EEID')
             AND NULLIF(TRIM(PERSON:"FIRST_NAME"::STRING),'') IS NOT NULL
             AND NULLIF(TRIM(PERSON:"LAST_NAME"::STRING),'') IS NOT NULL,
             'RESOLVED_FROM_STORED_USERLIST',
             'REVIEW_USER_NAME_OR_LOOKUP') AS RESOLUTION_STATUS
  FROM user_members
)
SELECT CONTENT_ID, ROLE_OR_ARCHER_FIELD, DISPLAY_NAME, RESOLUTION_STATUS
FROM role_names
UNION ALL
SELECT CONTENT_ID, ROLE_OR_ARCHER_FIELD, DISPLAY_NAME, RESOLUTION_STATUS
FROM user_names
ORDER BY CONTENT_ID, ROLE_OR_ARCHER_FIELD, DISPLAY_NAME;

-- ========================================================================
-- QUERY 2 — ENTITY/BUSINESS CONTENTID + LEVELID REFERENCES NOT YET NAMED
-- These SSP props are stored as JSON text. A valid name requires
-- joining to the ACTUAL referenced Archer record for that LevelId.
-- No guessed table names, fake entity names, or silent ContentId-only joins.
-- ========================================================================
WITH p AS (
  SELECT prop.SOURCE_RECORD_ID AS CONTENT_ID,
         prop.METADATA_JSON:"name"::STRING AS PROPERTY_NAME,
         TRY_PARSE_JSON(prop.METADATA_JSON:"value"::STRING) AS REF_JSON
  FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT prop
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY e
    ON e.FK_TARGET_ELEMENT_HASH=prop.PK_OSCAL_SSP_ELEMENT_HASH
   AND e.DEPENDENCY_TYPE='CONTAINS'
  JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT sc
    ON sc.PK_OSCAL_SSP_ELEMENT_HASH=e.FK_SOURCE_ELEMENT_HASH
   AND sc.ELEMENT_TYPE='system-characteristics'
   AND sc.SOURCE_RECORD_ID=prop.SOURCE_RECORD_ID
  WHERE prop.ELEMENT_TYPE='props'
    AND prop.SOURCE_SYSTEM_NAME='ARCHER'
    AND prop.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
    AND prop.METADATA_JSON:"name"::STRING IN ('entity','business')
)
SELECT p.CONTENT_ID AS AUTHORIZATION_PACKAGE_CONTENT_ID,
       UPPER(p.PROPERTY_NAME) AS ARCHER_FIELD,
       entry.VALUE:"ContentId"::STRING AS REFERENCED_CONTENT_ID,
       entry.VALUE:"LevelId"::STRING AS REFERENCED_LEVEL_ID,
       NULL::VARCHAR AS RESOLVED_DISPLAY_NAME,
       'LOOKUP_NOT_YET_VERIFIED' AS RESOLUTION_STATUS
FROM p,
     LATERAL FLATTEN(INPUT => p.REF_JSON) entry
WHERE entry.VALUE:"ContentId" IS NOT NULL
ORDER BY AUTHORIZATION_PACKAGE_CONTENT_ID, ARCHER_FIELD,
         REFERENCED_CONTENT_ID;

-- ========================================================================
-- QUERY 3 — OTHER REFERENCE-ID PROPERTIES (NOT DISPLAY NAMES)
-- These are currently retained as scalar reference IDs rather than
-- automatically hydrated business names. LevelId may not be available.
-- ========================================================================
SELECT prop.SOURCE_RECORD_ID AS AUTHORIZATION_PACKAGE_CONTENT_ID,
       UPPER(REPLACE(prop.METADATA_JSON:"name"::STRING,'-','_')) AS ARCHER_FIELD,
       prop.METADATA_JSON:"value"::STRING AS REFERENCED_ID,
       NULL::VARCHAR AS REFERENCED_LEVEL_ID,
       NULL::VARCHAR AS RESOLVED_DISPLAY_NAME,
       'REFERENCED_SOURCE_LOOKUP_REQUIRED' AS RESOLUTION_STATUS
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT prop
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY e
  ON e.FK_TARGET_ELEMENT_HASH=prop.PK_OSCAL_SSP_ELEMENT_HASH
 AND e.DEPENDENCY_TYPE='CONTAINS'
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT sc
  ON sc.PK_OSCAL_SSP_ELEMENT_HASH=e.FK_SOURCE_ELEMENT_HASH
 AND sc.SOURCE_RECORD_ID=prop.SOURCE_RECORD_ID
 AND sc.ELEMENT_TYPE='system-characteristics'
WHERE prop.ELEMENT_TYPE='props'
  AND prop.SOURCE_SYSTEM_NAME='ARCHER'
  AND prop.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
  AND prop.METADATA_JSON:"name"::STRING IN (
       'allocated-controls','archived-controls','inheritable-controls',
       'gs-lab-control-entity','allocated-controls-partial-control-providers'
  )
ORDER BY AUTHORIZATION_PACKAGE_CONTENT_ID, ARCHER_FIELD;

-- ========================================================================
-- QUERY 4 — FIND CANDIDATE ENTITY/BUSINESS/LEVEL/USER RAW TABLES
-- Metadata discovery only. Inspect the real table list before adding JOINs.
-- ========================================================================
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME
FROM RTX_RAW_DEV.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'ES_ESC_GRC'
  AND (TABLE_NAME ILIKE '%ENTITY%'
       OR TABLE_NAME ILIKE '%BUSINESS%'
       OR TABLE_NAME ILIKE '%LEVEL%'
       OR TABLE_NAME ILIKE '%USER%')
ORDER BY TABLE_NAME;

-- ========================================================================
-- QUERY 5 — FIND ACTUAL ID/JSON/DISPLAY-NAME COLUMN CONTRACTS
-- This does not assume the table or its display name column exists.
-- ========================================================================
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM RTX_RAW_DEV.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ES_ESC_GRC'
  AND (TABLE_NAME ILIKE '%ENTITY%'
       OR TABLE_NAME ILIKE '%BUSINESS%'
       OR TABLE_NAME ILIKE '%LEVEL%'
       OR TABLE_NAME ILIKE '%USER%')
  AND (COLUMN_NAME ILIKE '%CONTENT%'
       OR COLUMN_NAME ILIKE '%LEVEL%'
       OR COLUMN_NAME ILIKE '%NAME%'
       OR COLUMN_NAME ILIKE '%JSON%'
       OR COLUMN_NAME ILIKE '%TITLE%'
       OR COLUMN_NAME ILIKE '%ID%')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- ========================================================================
-- QUERY 6 — POAM ITEM IDENTITY IN PERSISTED OSCAL (NOT HUMAN-NAMED)
-- The Source One POAMS mapping creates item identities and UUIDs;
-- this query does not mislabel those as Archer item ContentIds.
-- ========================================================================
SELECT item.SOURCE_RECORD_ID AS AUTHORIZATION_PACKAGE_CONTENT_ID,
       item.OSCAL_UUID AS POAM_ITEM_OSCAL_UUID32,
       item.METADATA_JSON AS POAM_ITEM_PAYLOAD
FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_POAM_ELEMENT item
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_POAM_DEPENDENCY e
  ON e.FK_TARGET_ELEMENT_HASH=item.PK_DIM_OSCAL_POAM_ELEMENT_HASH
 AND e.DEPENDENCY_TYPE='CONTAINS'
JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_POAM_ELEMENT root
  ON root.PK_DIM_OSCAL_POAM_ELEMENT_HASH=e.FK_SOURCE_ELEMENT_HASH
 AND root.SOURCE_RECORD_ID=item.SOURCE_RECORD_ID
 AND root.ELEMENT_TYPE='plan-of-action-and-milestones'
WHERE item.ELEMENT_TYPE='poam-items'
  AND item.SOURCE_SYSTEM_NAME='ARCHER'
  AND item.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
ORDER BY AUTHORIZATION_PACKAGE_CONTENT_ID, POAM_ITEM_OSCAL_UUID32;

-- END. Nothing above changes OSCAL DIM/FACT, registry, mappings or source.
