-- SSP CIA obsolete fallback dependency safety preflight
-- READ ONLY | Snowflake DEV | 2026-10-12
-- Checks whether the 91 previously verified fallback property nodes have
-- exactly one CONTAINS parent and no outgoing or cross-record dependencies.
-- Do not delete stored nodes or links based solely on a summary count.

WITH fallback AS (
    SELECT
        PK_OSCAL_SSP_ELEMENT_HASH AS NODE_HASH,
        SOURCE_RECORD_ID,
        METADATA_JSON:"name"::STRING AS FALLBACK_FIELD
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT
    WHERE LOWER(ELEMENT_TYPE) = 'props'
      AND METADATA_JSON:"name"::STRING IN (
          'recommended-confidentiality-control-category',
          'confidentiality-control-category-override',
          'recommended-integrity-control-category',
          'integrity-control-category-override',
          'recommended-availability-control-category',
          'availability-control-category-override',
          'programsite-integrity-control-category',
          'programsite-availability-control-category',
          'cnss-confidentiality-rating',
          'cnss-integrity-rating',
          'cnss-availability-rating'
      )
),
incoming AS (
    SELECT
        n.NODE_HASH,
        COUNT(f.FK_TARGET_ELEMENT_HASH) AS INCOMING_LINKS,
        COUNT_IF(
            f.FK_TARGET_ELEMENT_HASH IS NOT NULL
            AND (
                f.DEPENDENCY_TYPE IS DISTINCT FROM 'CONTAINS'
                OR p.PK_OSCAL_SSP_ELEMENT_HASH IS NULL
                OR COALESCE(LOWER(p.ELEMENT_TYPE), '') <> 'system-characteristics'
                OR p.SOURCE_RECORD_ID IS DISTINCT FROM n.SOURCE_RECORD_ID
            )
        ) AS BAD_INCOMING_LINKS
    FROM fallback n
    LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY f
        ON f.FK_TARGET_ELEMENT_HASH = n.NODE_HASH
    LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT p
        ON p.PK_OSCAL_SSP_ELEMENT_HASH = f.FK_SOURCE_ELEMENT_HASH
    GROUP BY n.NODE_HASH
),
outgoing AS (
    SELECT
        n.NODE_HASH,
        COUNT(f.FK_SOURCE_ELEMENT_HASH) AS OUTGOING_LINKS
    FROM fallback n
    LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY f
        ON f.FK_SOURCE_ELEMENT_HASH = n.NODE_HASH
    GROUP BY n.NODE_HASH
)
SELECT
    IFF(GROUPING(n.FALLBACK_FIELD) = 1, 'ALL_FIELDS', n.FALLBACK_FIELD)
        AS FALLBACK_FIELD,
    COUNT(*) AS STORED_NODES,
    COUNT(DISTINCT n.SOURCE_RECORD_ID) AS SOURCE_RECORDS,
    SUM(i.INCOMING_LINKS) AS INCOMING_FACT_LINKS,
    SUM(o.OUTGOING_LINKS) AS OUTGOING_FACT_LINKS,
    SUM(i.BAD_INCOMING_LINKS) AS BAD_INCOMING_FACT_LINKS,
    COUNT_IF(
        i.INCOMING_LINKS <> 1
        OR o.OUTGOING_LINKS <> 0
        OR i.BAD_INCOMING_LINKS <> 0
    ) AS UNSAFE_NODES
FROM fallback n
JOIN incoming i ON i.NODE_HASH = n.NODE_HASH
JOIN outgoing o ON o.NODE_HASH = n.NODE_HASH
GROUP BY GROUPING SETS ((n.FALLBACK_FIELD), ())
ORDER BY FALLBACK_FIELD;

-- Expected against the October 12 owner-provided baseline:
-- ALL_FIELDS STORED_NODES = 91, INCOMING_FACT_LINKS = 91,
-- OUTGOING_FACT_LINKS = 0, BAD_INCOMING_FACT_LINKS = 0,
-- UNSAFE_NODES = 0.
-- An observed discrepancy is a STOP condition for migration planning.
