-- OSCAL Source One / SSP Control Implementation: all 50 APPROVED mapping rows
-- 2026-10-23 | Read-only Snowflake DEV QA. No DML/DDL or notebook variables.
-- Mapping source: simplify-metadata-boundary (CSV blob b9f982c445f293f9b5d47cab565194aa29ef8770).
-- Output is grouped per exact Archer field and QA_STATUS. This is NOT a load.
--
-- 46 system-characteristics props: validate source presence, parent->child FACT
--    relationship, explicit JSON null preservation, direct single scalar and
--    single Matillion-resolved select equality; structured json-text comparison
--    is performed on parsed JSON. Multi-valued/reference transforms remain
--    explicitly flagged for value-level inspection instead of falsely PASSing.
-- 2 responsible-party fields: match assignment role-id and FACT ownership;
--    party UUID/UserList membership equality still requires relationship QA.
-- 2 joined implemented-requirement fields: separately profile Level-355 RAW;
--    this is NOT parent-linked implemented-requirement value QA. Never interpret
--    those as absent from the Authorization Package root.
--
-- Duplicate RAW snapshots per Content ID are marked ambiguous, not silently
-- de-duplicated: the running mapper uses an ordering contract not replayed here.
-- All actual source values and results remain in Snowflake; Git stores SQL only.

WITH mapping_fields AS (
    SELECT column1::STRING AS FIELD_NAME,
           column2::STRING AS TARGET_PATH,
           column3::STRING AS TRANSFORM_ID,
           column4::STRING AS NULL_POLICY,
           column5::STRING AS STORAGE_ROUTE,
           column6::STRING AS TARGET_NAME
    FROM VALUES
    ('COUNT_OF_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls'),
    ('ALLOCATE_BASELINE_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'allocate-baseline-controls'),
    ('CONTROL_SET_VERSION_NUMBER', 'system-security-plan.system-characteristics.props[]', 'archer-select', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'control-set-version-number'),
    ('COUNT_OF_CONTROLS_WITHOUT_IMPLEMENTATION_DETAILS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls-without-implementation-details'),
    ('COUNT_OF_CONTROLS_WITH_OPEN_POAMS_ANDOR_RBDS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls-with-open-poams-andor-rbds'),
    ('NUMBER_OF_CONTROLS_BEING_INHERITED_BY_OTHERS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'number-of-controls-being-inherited-by-others'),
    ('ARCHIVE_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'archive-controls'),
    ('CONTROL_OWNER_CO', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'control-owner-co'),
    ('SECURITY_CONTROL_ASSESSOR_SCA', 'system-security-plan.metadata.responsible-parties[]', 'direct', 'omit', 'RESPONSIBLE_PARTY', 'security-control-assessor'),
    ('ADD_ADDITIONAL_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'add-additional-controls'),
    ('ALLOCATED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'reference-ids', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'allocated-controls'),
    ('ARCHIVED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'reference-ids', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'archived-controls'),
    ('INHERITED_CONTROL_SELECTION', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'inherited-control-selection'),
    ('INHERITABLE_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'reference-ids', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'inheritable-controls'),
    ('LINK_CNSS_CONTROLS_BY_CONFIDENTIALITY_RATING', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'link-cnss-controls-by-confidentiality-rating'),
    ('LINK_CNSS_CONTROLS_BY_INTEGRITY_RATING', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'link-cnss-controls-by-integrity-rating'),
    ('LINK_CNSS_CONTROLS_BY_AVAILABILITY_RATING', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'link-cnss-controls-by-availability-rating'),
    ('HELPER_ALLOCATED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'helper-allocated-controls'),
    ('PRECONTROL_ALLOCATION_PROGRESS_VIEW', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'precontrol-allocation-progress-view'),
    ('COUNT_OF_FULLY_IMPLEMENTED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-fully-implemented-controls'),
    ('CONTROL_SET_VERSION_NUMBER_HRC', 'system-security-plan.system-characteristics.props[]', 'archer-select', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'control-set-version-number-hrc'),
    ('GS_LAB_CONTROL_ENTITY', 'system-security-plan.system-characteristics.props[]', 'reference-ids', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'gs-lab-control-entity'),
    ('CONTROL_STANDARDS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'control-standards'),
    ('MASTER_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'master-controls'),
    ('ALLOCATED_CONTROLS_PARTIAL_CONTROL_PROVIDERS', 'system-security-plan.system-characteristics.props[]', 'reference-ids', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'allocated-controls-partial-control-providers'),
    ('ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA_TEXT', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'alternate-security-control-assessor-sca-text'),
    ('EXPORT_CONTROL_ASSESSOR_ECA_TEXT', 'system-security-plan.system-characteristics.props[]', 'text', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'export-control-assessor-eca-text'),
    ('SECURITY_CONTROL_ASSESSOR_SCA_TEXT', 'system-security-plan.system-characteristics.props[]', 'text', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'security-control-assessor-sca-text'),
    ('EXPORT_CONTROLLED_DATA_ITARAR_IF_APPLICABLE', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'export-controlled-data-itarar-if-applicable'),
    ('COUNT_OF_CONTROLS_WITH_OPEN_POAMS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls-with-open-poams'),
    ('COUNT_OF_CONTROLS_MISSING_POAMRBD', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls-missing-poamrbd'),
    ('ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA', 'system-security-plan.metadata.responsible-parties[]', 'direct', 'omit', 'RESPONSIBLE_PARTY', 'alternate-security-control-assessor'),
    ('ALLOCATED_CONTROLS_AUTHORIZATION_PACKAGE', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'allocated-controls-authorization-package'),
    ('CONTROL_SET_TO_ASSESS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'control-set-to-assess'),
    ('CHANGE_CONTROL', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'change-control'),
    ('HELPER_OTS_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'helper-ots-controls'),
    ('COUNT_OF_INHERITED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-inherited-controls'),
    ('COUNT_OF_ACTUAL_CONTROLS_IMPLEMENTED', 'system-security-plan.system-characteristics.props[]', 'direct', 'omit', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-actual-controls-implemented'),
    ('DATE_CONTINUE_TO_CONTROL_IMPLEMENTATION', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'date-continue-to-control-implementation'),
    ('_CURRENT_CONTROL_RISK_THRESHOLD', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'current-control-risk-threshold'),
    ('_OF_SATISFIED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'of-satisfied-controls'),
    ('CONTROL_NUMBER', 'system-security-plan.control-implementation.implemented-requirements[].control-id', 'text', 'omit', 'JOINED_REQUIREMENT', 'control-number'),
    ('IMPLEMENTATION_DETAILS', 'system-security-plan.control-implementation.implemented-requirements[].remarks', 'text', 'omit', 'JOINED_REQUIREMENT', 'implementation-details'),
    ('BASELINE_CONTROLS_ALLOCATED_DATE', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'baseline-controls-allocated-date'),
    ('CONTROL_RISK_APPETITE', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'control-risk-appetite'),
    ('PCT_CURRENT_CONTROL_RISK_THRESHOLD', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'pct-current-control-risk-threshold'),
    ('CONTROL_RISK_THRESHOLD_HELPER', 'system-security-plan.system-characteristics.props[]', 'json-text', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'control-risk-threshold-helper'),
    ('COUNT_OF_CONTROLS_NOT_ASSESSED', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-controls-not-assessed'),
    ('COUNT_OF_INHERITED_CONTROLS_THAT_HAVE_BEEN_ARCHIVED', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'count-of-inherited-controls-that-have-been-archived'),
    ('PCT_OF_SATISFIED_CONTROLS', 'system-security-plan.system-characteristics.props[]', 'direct', 'preserve', 'SYSTEM_CHARACTERISTICS_PROP', 'pct-of-satisfied-controls')
),
raw_package AS (
    SELECT CONTENT_ID::STRING AS CONTENT_ID,
           CURATED_JSON,
           COUNT(*) OVER (PARTITION BY CONTENT_ID::STRING) AS SOURCE_SNAPSHOTS
    FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW
),
source_field_values AS (
    SELECT p.CONTENT_ID,
           p.SOURCE_SNAPSHOTS,
           m.FIELD_NAME, m.TARGET_PATH, m.TRANSFORM_ID,
           m.NULL_POLICY, m.STORAGE_ROUTE, m.TARGET_NAME,
           GET(p.CURATED_JSON, m.FIELD_NAME) AS SOURCE_VALUE
    FROM raw_package p
    CROSS JOIN mapping_fields m
    WHERE m.STORAGE_ROUTE <> 'JOINED_REQUIREMENT'
),
source_prepared AS (
    SELECT s.*,
           TYPEOF(s.SOURCE_VALUE) AS SOURCE_TYPE,
           TO_JSON(s.SOURCE_VALUE) AS SOURCE_JSON,
           CASE
             WHEN s.SOURCE_VALUE IS NULL THEN 'SOURCE_KEY_ABSENT'
             WHEN IS_NULL_VALUE(s.SOURCE_VALUE) THEN 'SOURCE_JSON_NULL'
             WHEN TYPEOF(s.SOURCE_VALUE) = 'VARCHAR'
                  AND LENGTH(TRIM(s.SOURCE_VALUE::STRING)) = 0 THEN 'SOURCE_EMPTY'
             WHEN IS_ARRAY(s.SOURCE_VALUE)
                  AND ARRAY_SIZE(s.SOURCE_VALUE) = 0 THEN 'SOURCE_EMPTY'
             WHEN s.STORAGE_ROUTE = 'RESPONSIBLE_PARTY'
                  AND IS_OBJECT(s.SOURCE_VALUE)
                  AND COALESCE(ARRAY_SIZE(s.SOURCE_VALUE:"UserList"), 0) = 0
                  AND COALESCE(ARRAY_SIZE(s.SOURCE_VALUE:"GroupList"), 0) = 0
                  THEN 'SOURCE_EMPTY'
             WHEN s.TRANSFORM_ID = 'archer-select'
                  AND IS_ARRAY(s.SOURCE_VALUE:"ResolvedValues")
                  AND ARRAY_SIZE(s.SOURCE_VALUE:"ResolvedValues") = 0
                  THEN 'SOURCE_EMPTY'
             ELSE 'SOURCE_POPULATED'
           END AS SOURCE_STATE,
           CASE
             WHEN s.TRANSFORM_ID = 'json-text' THEN 'JSON_TEXT'
             WHEN s.TRANSFORM_ID IN ('direct', 'text', 'archer-select')
                  AND TYPEOF(s.SOURCE_VALUE)
                      IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE', 'BOOLEAN')
                  THEN 'SINGLE_SCALAR'
             WHEN s.TRANSFORM_ID = 'archer-select'
                  AND IS_ARRAY(s.SOURCE_VALUE:"ResolvedValues")
                  AND ARRAY_SIZE(s.SOURCE_VALUE:"ResolvedValues") = 1
                  AND COALESCE(
                        ARRAY_SIZE(s.SOURCE_VALUE:"ValuesListIds"),
                        ARRAY_SIZE(s.SOURCE_VALUE:"ValueListIds")
                      ) = 1
                  AND s.SOURCE_VALUE:"ResolvedValues"[0]:"LookupStatus"::STRING = 'MATCHED'
                  AND s.SOURCE_VALUE:"ResolvedValues"[0]:"ValueId"::STRING
                      = COALESCE(
                          s.SOURCE_VALUE:"ValuesListIds"[0]::STRING,
                          s.SOURCE_VALUE:"ValueListIds"[0]::STRING
                        )
                  THEN 'SINGLE_SCALAR'
             ELSE 'SHAPE_OR_MULTI_REVIEW'
           END AS MATCH_KIND,
           CASE
             WHEN s.TRANSFORM_ID IN ('direct', 'text', 'archer-select')
                  AND TYPEOF(s.SOURCE_VALUE)
                      IN ('VARCHAR', 'INTEGER', 'DECIMAL', 'DOUBLE', 'BOOLEAN')
                  THEN TRIM(s.SOURCE_VALUE::STRING)
             WHEN s.TRANSFORM_ID = 'archer-select'
                  AND IS_ARRAY(s.SOURCE_VALUE:"ResolvedValues")
                  AND ARRAY_SIZE(s.SOURCE_VALUE:"ResolvedValues") = 1
                  AND COALESCE(
                        ARRAY_SIZE(s.SOURCE_VALUE:"ValuesListIds"),
                        ARRAY_SIZE(s.SOURCE_VALUE:"ValueListIds")
                      ) = 1
                  AND s.SOURCE_VALUE:"ResolvedValues"[0]:"LookupStatus"::STRING = 'MATCHED'
                  AND s.SOURCE_VALUE:"ResolvedValues"[0]:"ValueId"::STRING
                      = COALESCE(
                          s.SOURCE_VALUE:"ValuesListIds"[0]::STRING,
                          s.SOURCE_VALUE:"ValueListIds"[0]::STRING
                        )
                  THEN TRIM(s.SOURCE_VALUE:"ResolvedValues"[0]:"ValueName"::STRING)
             ELSE NULL
           END AS EXPECTED_SCALAR
    FROM source_field_values s
),
property_target AS (
    SELECT parent.SOURCE_RECORD_ID AS CONTENT_ID,
           'SYSTEM_CHARACTERISTICS_PROP' AS STORAGE_ROUTE,
           child.METADATA_JSON:"name"::STRING AS TARGET_NAME,
           child.METADATA_JSON:"value" AS TARGET_VALUE
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT parent
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY rel
      ON rel.FK_SOURCE_ELEMENT_HASH = parent.PK_OSCAL_SSP_ELEMENT_HASH
     AND rel.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT child
      ON child.PK_OSCAL_SSP_ELEMENT_HASH = rel.FK_TARGET_ELEMENT_HASH
    WHERE parent.ELEMENT_TYPE = 'system-characteristics'
      AND child.ELEMENT_TYPE = 'props'
      AND parent.SOURCE_SYSTEM_NAME = 'ARCHER'
      AND parent.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND child.SOURCE_SYSTEM_NAME = parent.SOURCE_SYSTEM_NAME
      AND child.SOURCE_TABLE_NAME = parent.SOURCE_TABLE_NAME
      AND child.SOURCE_RECORD_ID = parent.SOURCE_RECORD_ID
),
party_assignment_target AS (
    SELECT parent.SOURCE_RECORD_ID AS CONTENT_ID,
           'RESPONSIBLE_PARTY' AS STORAGE_ROUTE,
           child.METADATA_JSON:"role-id"::STRING AS TARGET_NAME,
           child.METADATA_JSON:"party-uuids" AS TARGET_VALUE
    FROM RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT parent
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.FACT_OSCAL_SSP_DEPENDENCY rel
      ON rel.FK_SOURCE_ELEMENT_HASH = parent.PK_OSCAL_SSP_ELEMENT_HASH
     AND rel.DEPENDENCY_TYPE = 'CONTAINS'
    JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT child
      ON child.PK_OSCAL_SSP_ELEMENT_HASH = rel.FK_TARGET_ELEMENT_HASH
    WHERE parent.ELEMENT_TYPE = 'metadata'
      AND child.ELEMENT_TYPE = 'responsible-parties'
      AND parent.SOURCE_SYSTEM_NAME = 'ARCHER'
      AND parent.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND child.SOURCE_SYSTEM_NAME = parent.SOURCE_SYSTEM_NAME
      AND child.SOURCE_TABLE_NAME = parent.SOURCE_TABLE_NAME
      AND child.SOURCE_RECORD_ID = parent.SOURCE_RECORD_ID
),
target_values AS (
    SELECT * FROM property_target
    UNION ALL
    SELECT * FROM party_assignment_target
),
record_reconciliation AS (
    SELECT s.CONTENT_ID, s.FIELD_NAME, s.TARGET_PATH,
           s.TRANSFORM_ID, s.NULL_POLICY, s.STORAGE_ROUTE,
           s.SOURCE_SNAPSHOTS, s.SOURCE_STATE,
           s.SOURCE_TYPE, s.SOURCE_JSON, s.MATCH_KIND, s.EXPECTED_SCALAR,
           COUNT(t.TARGET_NAME) AS TARGET_ELEMENTS,
           COALESCE(COUNT_IF(IS_NULL_VALUE(t.TARGET_VALUE)), 0) AS TARGET_JSON_NULL_ELEMENTS,
           COALESCE(COUNT_IF(
               CASE
                 WHEN s.MATCH_KIND = 'SINGLE_SCALAR'
                      THEN t.TARGET_VALUE::STRING = s.EXPECTED_SCALAR
                 WHEN s.MATCH_KIND = 'JSON_TEXT'
                      THEN TRY_PARSE_JSON(t.TARGET_VALUE::STRING)
                           = TRY_PARSE_JSON(s.SOURCE_JSON)
                 ELSE FALSE
               END
           ), 0) AS MATCHED_ELEMENTS
    FROM source_prepared s
    LEFT JOIN target_values t
      ON t.CONTENT_ID = s.CONTENT_ID
     AND t.STORAGE_ROUTE = s.STORAGE_ROUTE
     AND t.TARGET_NAME = s.TARGET_NAME
    GROUP BY ALL
),
classified AS (
    SELECT *,
           CASE
             WHEN SOURCE_SNAPSHOTS > 1 THEN 'SOURCE_SNAPSHOT_AMBIGUOUS'
             WHEN SOURCE_STATE = 'SOURCE_KEY_ABSENT' AND TARGET_ELEMENTS > 0
                  THEN 'UNEXPECTED_TARGET_FOR_ABSENT_SOURCE'
             WHEN SOURCE_STATE = 'SOURCE_KEY_ABSENT' THEN 'SOURCE_KEY_ABSENT'
             WHEN SOURCE_STATE = 'SOURCE_EMPTY' AND TARGET_ELEMENTS > 0
                  THEN 'UNEXPECTED_TARGET_FOR_EMPTY_SOURCE'
             WHEN SOURCE_STATE = 'SOURCE_EMPTY' THEN 'SOURCE_EMPTY'
             WHEN SOURCE_STATE = 'SOURCE_JSON_NULL' AND NULL_POLICY = 'preserve'
                  AND TARGET_ELEMENTS = 1 AND TARGET_JSON_NULL_ELEMENTS = 1
                  THEN 'EXPLICIT_NULL_PRESERVED'
             WHEN SOURCE_STATE = 'SOURCE_JSON_NULL' AND NULL_POLICY = 'preserve'
                  AND TARGET_ELEMENTS = 0 THEN 'NULL_SOURCE_TARGET_MISSING'
             WHEN SOURCE_STATE = 'SOURCE_JSON_NULL' AND NULL_POLICY = 'preserve'
                  THEN 'NULL_SOURCE_TARGET_CONFLICT'
             WHEN SOURCE_STATE = 'SOURCE_JSON_NULL' AND TARGET_ELEMENTS > 0
                  THEN 'UNEXPECTED_TARGET_FOR_OMITTED_NULL'
             WHEN SOURCE_STATE = 'SOURCE_JSON_NULL' THEN 'SOURCE_NULL_OMITTED'
             WHEN TARGET_ELEMENTS = 0 THEN 'POPULATED_SOURCE_TARGET_MISSING'
             WHEN STORAGE_ROUTE = 'RESPONSIBLE_PARTY'
                  THEN 'ROLE_ASSIGNMENT_PRESENT_IDENTITY_REVIEW'
             WHEN MATCH_KIND IN ('SINGLE_SCALAR', 'JSON_TEXT')
                  AND MATCHED_ELEMENTS = 1 AND TARGET_ELEMENTS = 1
                  THEN 'VALUE_MATCH'
             WHEN MATCH_KIND IN ('SINGLE_SCALAR', 'JSON_TEXT')
                  AND MATCHED_ELEMENTS = 0 THEN 'VALUE_MISMATCH'
             WHEN MATCHED_ELEMENTS > 0 AND TARGET_ELEMENTS > 1
                  THEN 'EXTRA_TARGET_ELEMENTS_REVIEW'
             ELSE 'TARGET_PRESENT_SHAPE_OR_MULTI_REVIEW'
           END AS QA_STATUS
    FROM record_reconciliation
),
root_field_summary AS (
    SELECT FIELD_NAME, TARGET_PATH, STORAGE_ROUTE, TRANSFORM_ID,
           NULL_POLICY, QA_STATUS,
           COUNT(*) AS SOURCE_ROWS,
           COUNT(DISTINCT CONTENT_ID) AS DISTINCT_RECORDS,
           MIN(CONTENT_ID) AS EXAMPLE_SOURCE_ID
    FROM classified
    GROUP BY FIELD_NAME, TARGET_PATH, STORAGE_ROUTE,
             TRANSFORM_ID, NULL_POLICY, QA_STATUS
),
joined_field_summary AS (
    SELECT m.FIELD_NAME, m.TARGET_PATH, m.STORAGE_ROUTE, m.TRANSFORM_ID,
           m.NULL_POLICY,
           CASE
             WHEN COALESCE(COUNT_IF(
                 GET(j.CURATED_JSON, m.FIELD_NAME) IS NOT NULL
                 AND NOT COALESCE(IS_NULL_VALUE(GET(j.CURATED_JSON, m.FIELD_NAME)), FALSE)
               ), 0) > 0
               THEN 'JOINED_SOURCE_PRESENT_PARENT_TARGET_QA_PENDING'
             WHEN COUNT(j.CONTENT_ID) = 0 THEN 'NO_JOINED_SOURCE_ROWS'
             ELSE 'JOINED_SOURCE_EMPTY_OR_NULL'
           END AS QA_STATUS,
           COUNT(j.CONTENT_ID) AS SOURCE_ROWS,
           COUNT(DISTINCT j.CONTENT_ID::STRING) AS DISTINCT_RECORDS,
           MIN(j.CONTENT_ID::STRING) AS EXAMPLE_SOURCE_ID
    FROM mapping_fields m
    LEFT JOIN RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_ALLOCATED_CONTROLS_CONTROL_RAW j
      ON TRUE
    WHERE m.STORAGE_ROUTE = 'JOINED_REQUIREMENT'
    GROUP BY m.FIELD_NAME, m.TARGET_PATH, m.STORAGE_ROUTE,
             m.TRANSFORM_ID, m.NULL_POLICY
)
SELECT FIELD_NAME AS ARCHER_FIELD_NAME,
       STORAGE_ROUTE AS TARGET_KIND,
       TARGET_PATH AS OSCAL_TARGET_PATH,
       TRANSFORM_ID,
       NULL_POLICY,
       QA_STATUS,
       SOURCE_ROWS,
       DISTINCT_RECORDS,
       EXAMPLE_SOURCE_ID
FROM root_field_summary
UNION ALL
SELECT FIELD_NAME, STORAGE_ROUTE, TARGET_PATH, TRANSFORM_ID,
       NULL_POLICY, QA_STATUS, SOURCE_ROWS, DISTINCT_RECORDS, EXAMPLE_SOURCE_ID
FROM joined_field_summary
ORDER BY
    CASE
      WHEN QA_STATUS IN ('POPULATED_SOURCE_TARGET_MISSING', 'VALUE_MISMATCH',
          'NULL_SOURCE_TARGET_MISSING', 'NULL_SOURCE_TARGET_CONFLICT',
          'UNEXPECTED_TARGET_FOR_ABSENT_SOURCE', 'UNEXPECTED_TARGET_FOR_EMPTY_SOURCE',
          'UNEXPECTED_TARGET_FOR_OMITTED_NULL', 'EXTRA_TARGET_ELEMENTS_REVIEW') THEN 0
      WHEN QA_STATUS IN ('SOURCE_SNAPSHOT_AMBIGUOUS',
          'TARGET_PRESENT_SHAPE_OR_MULTI_REVIEW',
          'ROLE_ASSIGNMENT_PRESENT_IDENTITY_REVIEW',
          'JOINED_SOURCE_PRESENT_PARENT_TARGET_QA_PENDING') THEN 1
      ELSE 2
    END,
    ARCHER_FIELD_NAME, QA_STATUS;
