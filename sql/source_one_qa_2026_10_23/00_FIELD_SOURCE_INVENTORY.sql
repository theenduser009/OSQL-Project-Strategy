-- OSCAL QA scope: 25 named Archer fields visible in owner's screenshot ONLY.
-- Snapshot: 2026-10-23; mapping CSV blob b9f982c445f293f9b5d47cab565194aa29ef8770.
-- Read-only Snowflake DEV field inventory; NO target equality claim.
-- Source may have multiple raw snapshots of one Content ID; the count
-- AMBIGUOUS_SNAPSHOTS identifies that gap rather than choosing silently.
-- Screenshot row 18 is malformed/shifted (not a verifiable Archer field);
-- row 26 BASELINE_RECOMMENDATION is visible but unnumbered.
-- 'DEFERRED' fields are source-profiled, never called mapped/PASS.
WITH field_contract AS (
  SELECT column1::STRING AS ARCHER_FIELD_NAME,
         column2::STRING AS OSCAL_MODEL,
         column3::STRING AS OSCAL_PATH,
         column4::STRING AS EXECUTION_STATUS,
         column5::STRING AS TRANSFORM_ID,
         column6::STRING AS NULL_POLICY
  FROM VALUES
    ('INFORMATION_SYSTEM_TYPE', 'SSP - System Characteristics', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'archer-select', 'preserve'),
    ('REQUEST_TO_BEGIN_ASSESSMENT', 'Security Assessment Plan', 'assessment-plan.tasks[].props[]', 'APPROVED', 'archer-select', 'preserve'),
    ('APPROVAL_TO_BEGIN_ASSESSMENT', 'Security Assessment Plan', 'assessment-plan.tasks[].props[]', 'APPROVED', 'archer-select', 'preserve'),
    ('PREASSESSMENT_REVIEW_COMMENTS', 'Security Assessment Plan', 'assessment-plan.tasks[].remarks', 'APPROVED', 'text', 'preserve'),
    ('PCT_CURRENT_CONTROL_RISK_THRESHOLD', 'SSP - Control Implementation', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'direct', 'preserve'),
    ('PCT_OF_SATISFIED_CONTROLS', 'SSP - Control Implementation', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'direct', 'preserve'),
    ('SECURITY_CONTROL_ASSESSOR_SCA', 'SSP - Control Implementation', 'system-security-plan.metadata.responsible-parties[]', 'APPROVED', 'direct', 'omit'),
    ('LINK_CNSS_CONTROLS_BY_AVAILABILITY_RATING', 'SSP - Control Implementation', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'direct', 'preserve'),
    ('EXPORT_CONTROLLED_DATA_ITARAR_IF_APPLICABLE', 'SSP - Control Implementation', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'direct', 'preserve'),
    ('ALTERNATE_SECURITY_CONTROL_ASSESSOR_SCA', 'SSP - Control Implementation', 'system-security-plan.metadata.responsible-parties[]', 'APPROVED', 'direct', 'omit'),
    ('HELPER_ALLOCATED_CONTROLS', 'SSP - Control Implementation', 'system-security-plan.system-characteristics.props[]', 'APPROVED', 'json-text', 'preserve'),
    ('SUBSYSTEMS', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('SOFTWARE', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('HARDWARE', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('INTERCONNECTIONS', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('INTERCONNECTIONS_CONNECTING_INFORMATION_SYSTEM', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('SAP_INTAKE_FORM_INTERCONNECTIONS', 'SSP - System Implementation', 'system-security-plan.system-implementation.components[]', 'APPROVED', 'direct', 'omit'),
    ('FINDINGS', 'Assessment Results', 'assessment-results.results[].props[]', 'APPROVED', 'direct', 'preserve'),
    ('RISK_ACCEPTANCE_RBDS', 'Assessment Results', 'assessment-results.results[].props[]', 'APPROVED', 'reference-ids', 'omit'),
    ('PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD', 'Assessment Results', 'assessment-results.results[].observations[]', 'APPROVED', 'scalar-score', 'omit'),
    ('PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD', 'Assessment Results', 'assessment-results.results[].observations[]', 'APPROVED', 'scalar-score', 'omit'),
    ('RISK_ASSESSMENT_REPORT', 'Assessment Results', 'assessment-results.results[].props[]', 'APPROVED', 'json-text', 'omit'),
    ('DUE_DATE', 'Assessment Results', 'assessment-results.results[].props[]', 'APPROVED', 'date', 'omit'),
    ('ADD_OVERLAY', 'Profile', 'Multiple — see notes', 'DEFERRED', 'UNASSIGNED', 'omit'),
    ('BASELINE_RECOMMENDATION', 'Profile', 'profile.imports[]', 'DEFERRED', 'UNASSIGNED', 'omit')
),
source_rows AS (
  SELECT CONTENT_ID::STRING AS CONTENT_ID,
         CURATED_JSON,
         COUNT(*) OVER (PARTITION BY CONTENT_ID::STRING) AS SOURCE_SNAPSHOTS
  FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW
),
field_instances AS (
  SELECT f.*,
         s.CONTENT_ID,
         s.SOURCE_SNAPSHOTS,
         GET(s.CURATED_JSON, f.ARCHER_FIELD_NAME) AS SOURCE_VALUE
  FROM source_rows s CROSS JOIN field_contract f
),
classified AS (
  SELECT *,
         TYPEOF(SOURCE_VALUE) AS SOURCE_JSON_TYPE,
         CASE
           WHEN SOURCE_VALUE IS NULL THEN 'SOURCE_KEY_ABSENT'
           WHEN IS_NULL_VALUE(SOURCE_VALUE) THEN 'EXPLICIT_JSON_NULL'
           WHEN TYPEOF(SOURCE_VALUE) = 'VARCHAR'
                AND LENGTH(TRIM(SOURCE_VALUE::STRING)) = 0 THEN 'SOURCE_EMPTY'
           WHEN IS_ARRAY(SOURCE_VALUE)
                AND ARRAY_SIZE(SOURCE_VALUE) = 0 THEN 'SOURCE_EMPTY'
           WHEN IS_OBJECT(SOURCE_VALUE)
                AND ARRAY_SIZE(OBJECT_KEYS(SOURCE_VALUE)) = 0 THEN 'SOURCE_EMPTY'
           ELSE 'SOURCE_POPULATED'
         END AS SOURCE_STATE
  FROM field_instances
)
SELECT ARCHER_FIELD_NAME, OSCAL_MODEL, OSCAL_PATH, EXECUTION_STATUS,
       TRANSFORM_ID, NULL_POLICY, SOURCE_STATE, SOURCE_JSON_TYPE,
       COUNT(*) AS RAW_ROWS,
       COUNT(DISTINCT CONTENT_ID) AS DISTINCT_CONTENT_IDS,
       COUNT_IF(SOURCE_SNAPSHOTS > 1) AS AMBIGUOUS_SNAPSHOT_ROWS
FROM classified
GROUP BY ARCHER_FIELD_NAME, OSCAL_MODEL, OSCAL_PATH, EXECUTION_STATUS,
         TRANSFORM_ID, NULL_POLICY, SOURCE_STATE, SOURCE_JSON_TYPE
ORDER BY ARCHER_FIELD_NAME, SOURCE_STATE, SOURCE_JSON_TYPE;
