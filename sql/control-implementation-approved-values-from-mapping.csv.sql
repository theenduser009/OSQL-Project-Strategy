-- SSP Control Implementation: approved source fields and stored OSCAL values.
-- Read-only SQL. The mapping CSV is read at query time (no mapping inventory
-- or environment identifiers are hard-coded in this public example).
-- Replace the four table-name placeholders and the CSV stage path.
-- The staged CSV is the approved source-field mapping input.
--
-- Output: original Archer field name, logical source table, OSCAL path,
-- parent source record ID, actual OSCAL value and value status.
-- Up to 3 persisted examples per APPROVED mapped field, populated first.
-- Empty-source/null-only mappings remain distinguishable. This query
-- inspects stored values; it is NOT a raw-source-to-target equality test.

SET SSP_DIM = '<CURATED_DB>.<SCHEMA>.<SSP_DIM_TABLE>';
SET SSP_FACT = '<CURATED_DB>.<SCHEMA>.<SSP_FACT_TABLE>';
SET PACKAGE_SOURCE = '<RAW_DB>.<SCHEMA>.<PACKAGE_SOURCE_TABLE>';
SET CONTROL_SOURCE = '<RAW_DB>.<SCHEMA>.<CONTROL_DETAIL_SOURCE_TABLE>';

WITH approved_csv AS (
    SELECT
        TRIM(t.$1::STRING) AS ARCHER_SQL_FIELD,
        TRIM(t.$3::STRING) AS OSCAL_TARGET_PATH,
        TRIM(t.$15::STRING) AS ROLE_ID
    FROM @<MAPPING_STAGE>/ARCHER_OSCAL_MAPPINGS.csv
         (FILE_FORMAT => (
             TYPE => 'CSV',
             SKIP_HEADER => 1,
             FIELD_OPTIONALLY_ENCLOSED_BY => '"'
         )) t
    WHERE TRIM(t.$2::STRING) = 'SSP - Control Implementation'
      AND UPPER(TRIM(t.$5::STRING)) = 'APPROVED'
),
mapped AS (
    SELECT
        ARCHER_SQL_FIELD,
        OSCAL_TARGET_PATH,
        CASE
          WHEN OSCAL_TARGET_PATH =
              'system-security-plan.system-characteristics.props[]'
            THEN 'PACKAGE_PROP'
          WHEN OSCAL_TARGET_PATH =
              'system-security-plan.metadata.responsible-parties[]'
            THEN 'ASSESSOR_ROLE'
          WHEN OSCAL_TARGET_PATH LIKE
              'system-security-plan.control-implementation.implemented-requirements[].%'
            THEN 'REQUIREMENT_MEMBER'
          ELSE 'UNHANDLED_TARGET'
        END AS SOURCE_SCOPE,
        REGEXP_REPLACE(LOWER(ARCHER_SQL_FIELD), '[^a-z0-9]+', '-')
            AS PROP_NAME,
        ROLE_ID,
        REGEXP_SUBSTR(OSCAL_TARGET_PATH, '[^.]+$') AS MEMBER_NAME
    FROM approved_csv
),
values_found AS (
    -- Package-wide properties, owned by system-characteristics.
    SELECT m.ARCHER_SQL_FIELD, sc.SOURCE_RECORD_ID,
           p.OSCAL_UUID, p.METADATA_JSON:"value" AS OSCAL_VALUE
    FROM IDENTIFIER($SSP_DIM) sc
    JOIN IDENTIFIER($SSP_FACT) e
      ON e.FK_SOURCE_ELEMENT_HASH = sc.PK_OSCAL_SSP_ELEMENT_HASH
     AND e.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN IDENTIFIER($SSP_DIM) p
      ON p.PK_OSCAL_SSP_ELEMENT_HASH = e.FK_TARGET_ELEMENT_HASH
    JOIN mapped m
      ON m.SOURCE_SCOPE = 'PACKAGE_PROP'
     AND p.METADATA_JSON:"name"::STRING = m.PROP_NAME
    WHERE sc.ELEMENT_TYPE = 'system-characteristics'
      AND p.ELEMENT_TYPE = 'props'
      AND sc.SOURCE_RECORD_ID = p.SOURCE_RECORD_ID

    UNION ALL

    -- Responsible-party assignments.
    SELECT m.ARCHER_SQL_FIELD, rp.SOURCE_RECORD_ID,
           rp.OSCAL_UUID, rp.METADATA_JSON:"party-uuids" AS OSCAL_VALUE
    FROM IDENTIFIER($SSP_DIM) md
    JOIN IDENTIFIER($SSP_FACT) e
      ON e.FK_SOURCE_ELEMENT_HASH = md.PK_OSCAL_SSP_ELEMENT_HASH
     AND e.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN IDENTIFIER($SSP_DIM) rp
      ON rp.PK_OSCAL_SSP_ELEMENT_HASH = e.FK_TARGET_ELEMENT_HASH
    JOIN mapped m
      ON m.SOURCE_SCOPE = 'ASSESSOR_ROLE'
     AND rp.METADATA_JSON:"role-id"::STRING = m.ROLE_ID
    WHERE md.ELEMENT_TYPE = 'metadata'
      AND rp.ELEMENT_TYPE = 'responsible-parties'
      AND md.SOURCE_RECORD_ID = rp.SOURCE_RECORD_ID

    UNION ALL

    -- Individual requirements: native members such as control-id and remarks.
    SELECT m.ARCHER_SQL_FIELD, req.SOURCE_RECORD_ID,
           req.OSCAL_UUID, GET(req.METADATA_JSON, m.MEMBER_NAME) AS OSCAL_VALUE
    FROM IDENTIFIER($SSP_DIM) req
    JOIN mapped m
      ON m.SOURCE_SCOPE = 'REQUIREMENT_MEMBER'
    WHERE req.ELEMENT_TYPE = 'implemented-requirements'
),
ranked AS (
    SELECT v.*,
        ROW_NUMBER() OVER (
            PARTITION BY v.ARCHER_SQL_FIELD
            ORDER BY IFF(
                v.OSCAL_VALUE IS NOT NULL
                AND NOT IS_NULL_VALUE(v.OSCAL_VALUE), 0, 1
            ), v.SOURCE_RECORD_ID, v.OSCAL_UUID
        ) AS SAMPLE_N
    FROM values_found v
)
SELECT
    m.ARCHER_SQL_FIELD,
    IFF(m.SOURCE_SCOPE = 'REQUIREMENT_MEMBER',
        $CONTROL_SOURCE, $PACKAGE_SOURCE) AS ARCHER_SOURCE_TABLE,
    m.OSCAL_TARGET_PATH,
    r.SOURCE_RECORD_ID,
    r.OSCAL_UUID,
    r.OSCAL_VALUE,
    CASE
      WHEN m.SOURCE_SCOPE = 'UNHANDLED_TARGET'
        THEN 'UNHANDLED_TARGET'
      WHEN r.SOURCE_RECORD_ID IS NULL
        THEN 'NO_PERSISTED_EXAMPLE'
      WHEN r.OSCAL_VALUE IS NULL OR IS_NULL_VALUE(r.OSCAL_VALUE)
        THEN 'NULL_VALUE'
      ELSE 'POPULATED_VALUE'
    END AS VALUE_STATUS
FROM mapped m
LEFT JOIN ranked r
  ON r.ARCHER_SQL_FIELD = m.ARCHER_SQL_FIELD
 AND r.SAMPLE_N <= 3
ORDER BY m.ARCHER_SQL_FIELD, r.SAMPLE_N;
