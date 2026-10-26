-- 20 unhighlighted fields from the October 26 Archer QA screenshot.
-- Read only. Shows up to 3 Content IDs per field (populated first).
-- Output: Content ID, Archer field, source value, DIM table, path,
-- element type, OSCAL property/member name, actual target value.
-- Blank target = no matching DIM row; deferred/blocked fields have none.
WITH fields AS (
 SELECT column1::INT N, column2::STRING FIELD_NAME,
        column3::STRING KIND, column4::STRING PROPERTY_NAME,
        column5::STRING REF_TYPE
 FROM VALUES
 (5,'PCT_CURRENT_CONTROL_RISK_THRESHOLD','SC','pct-current-control-risk-threshold',NULL),
 (6,'PCT_OF_SATISFIED_CONTROLS','SC','pct-of-satisfied-controls',NULL),
 (7,'SECURITY_CONTROL_ASSESSOR_SCA','ROLE','security-control-assessor',NULL),
 (12,'SUBSYSTEMS','COMP','type','system'),
 (13,'SOFTWARE','COMP','type','software'),
 (14,'HARDWARE','COMP','type','hardware'),
 (15,'INTERCONNECTIONS','COMP','type','interconnection'),
 (16,'INTERCONNECTIONS_CONNECTING_INFORMATION_SYSTEM','COMP','type','interconnection'),
 (17,'SAP_INTAKE_FORM_INTERCONNECTIONS','COMP','type','interconnection'),
 (19,'FINDINGS','ARP','findings',NULL),
 (20,'RISK_ACCEPTANCE_RBDS','ARP','risk-acceptance-rbds',NULL),
 (21,'PCT_CURRENT_HIGHEST_DEVICE_RISK_THRESHOLD','ARO','pct-current-highest-device-risk-threshold',NULL),
 (22,'PCT_CURRENT_AVERAGE_DEVICE_RISK_THRESHOLD','ARO','pct-current-average-device-risk-threshold',NULL),
 (23,'RISK_ASSESSMENT_REPORT','ARP','risk-assessment-report',NULL),
 (24,'DUE_DATE','ARP','due-date',NULL),
 (25,'ADD_OVERLAY','NONE',NULL,NULL),
 (26,'BASELINE_RECOMMENDATION','NONE',NULL,NULL),
 (27,'POAMS','POAM','uuid',NULL),
 (28,'PORTS_PROTOCOLS_AND_SERVICES_MANAGEMENT_PPSM','NONE',NULL,NULL),
 (29,'RECOMMENDED_SECURITY_CATEGORY','NONE',NULL,NULL)
),
raw_values AS (
 SELECT f.*, a.CONTENT_ID::STRING CID, GET(a.CURATED_JSON,f.FIELD_NAME) SRC
 FROM RTX_RAW_DEV.ES_ESC_GRC.ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW a
 CROSS JOIN fields f
),
examples AS (
 SELECT *, ROW_NUMBER() OVER (PARTITION BY FIELD_NAME ORDER BY
     IFF(SRC IS NULL OR IS_NULL_VALUE(SRC) OR
         (IS_ARRAY(SRC) AND ARRAY_SIZE(SRC)=0),1,0), CID) RN
 FROM raw_values
 QUALIFY RN<=3
),
refs AS (
 SELECT e.*, x.VALUE ITEM,
        IFF(e.KIND IN ('COMP','POAM'),
            IFF(IS_OBJECT(x.VALUE), x.VALUE:"ContentId"::STRING,
                x.VALUE::STRING), NULL) REF_ID
 FROM examples e, LATERAL FLATTEN(
    INPUT => CASE WHEN e.KIND IN ('COMP','POAM') AND IS_ARRAY(e.SRC)
             THEN e.SRC ELSE ARRAY_CONSTRUCT(e.SRC) END,
    OUTER => TRUE) x
)
SELECT
 r.CID AS ARCHER_CONTENT_ID,
 r.FIELD_NAME AS ARCHER_FIELD_NAME,
 CASE WHEN r.SRC IS NULL THEN NULL
      WHEN IS_NULL_VALUE(r.SRC) THEN 'null'
      WHEN r.KIND IN ('COMP','POAM') THEN TO_JSON(r.ITEM)
      WHEN TYPEOF(r.SRC)='VARCHAR' THEN r.SRC::STRING
      ELSE TO_JSON(r.SRC) END AS SOURCE_VALUE,
 CASE WHEN r.KIND IN ('SC','ROLE','COMP') THEN 'DIM_OSCAL_SSP_ELEMENT'
      WHEN r.KIND IN ('ARP','ARO') THEN 'DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT'
      WHEN r.KIND='POAM' THEN 'DIM_OSCAL_POAM_ELEMENT' END AS DIM_TABLE,
 CASE r.KIND
   WHEN 'SC' THEN 'system-security-plan.system-characteristics.props[]'
   WHEN 'ROLE' THEN 'system-security-plan.metadata.responsible-parties[]'
   WHEN 'COMP' THEN 'system-security-plan.system-implementation.components[]'
   WHEN 'ARP' THEN 'assessment-results.results[].props[]'
   WHEN 'ARO' THEN 'assessment-results.results[].observations[]'
   WHEN 'POAM' THEN 'plan-of-action-and-milestones.poam-items[]'
 END AS OSCAL_ELEMENT_PATH,
 COALESCE(s.ELEMENT_TYPE,a.ELEMENT_TYPE,p.ELEMENT_TYPE) AS ELEMENT_TYPE,
 r.PROPERTY_NAME AS OSCAL_FIELD_NAME,
 CASE
   WHEN r.KIND='SC' THEN IFF(IS_NULL_VALUE(s.METADATA_JSON:"value"),'null',s.METADATA_JSON:"value"::STRING)
   WHEN r.KIND='ROLE' THEN TO_JSON(s.METADATA_JSON:"party-uuids")
   WHEN r.KIND='COMP' AND s.PK_OSCAL_SSP_ELEMENT_HASH IS NOT NULL THEN
        TO_JSON(OBJECT_CONSTRUCT_KEEP_NULL('type',s.METADATA_JSON:"type"::STRING,
             'title',s.METADATA_JSON:"title"::STRING,
             'description',s.METADATA_JSON:"description"::STRING))
   WHEN r.KIND='ARP' THEN IFF(IS_NULL_VALUE(a.METADATA_JSON:"value"),'null',a.METADATA_JSON:"value"::STRING)
   WHEN r.KIND='ARO' THEN IFF(IS_NULL_VALUE(a.METADATA_JSON:"props"[0]:"value"),'null',a.METADATA_JSON:"props"[0]:"value"::STRING)
   WHEN r.KIND='POAM' THEN p.OSCAL_UUID
 END AS TARGET_VALUE
FROM refs r
LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_SSP_ELEMENT s
  ON r.KIND IN ('SC','ROLE','COMP')
 AND s.SOURCE_RECORD_ID=r.CID
 AND s.SOURCE_SYSTEM_NAME='ARCHER'
 AND s.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
 AND ((r.KIND='SC' AND s.ELEMENT_TYPE='props' AND s.METADATA_JSON:"name"::STRING=r.PROPERTY_NAME)
   OR (r.KIND='ROLE' AND s.ELEMENT_TYPE='responsible-parties'
                     AND s.METADATA_JSON:"role-id"::STRING=r.PROPERTY_NAME)
   OR (r.KIND='COMP' AND s.ELEMENT_TYPE='components'
       AND s.METADATA_JSON:"type"::STRING=r.REF_TYPE
       AND s.PK_OSCAL_SSP_ELEMENT_HASH=MD5_BINARY(CONCAT_WS('|',
         'v1_registry_path_instance','ARCHER','ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW',
         r.CID,'SSP','system-security-plan.system-implementation.components[]',r.REF_ID))))
LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_ASSESSMENT_RESULTS_ELEMENT a
  ON r.KIND IN ('ARP','ARO')
 AND a.SOURCE_RECORD_ID=r.CID
 AND a.SOURCE_SYSTEM_NAME='ARCHER'
 AND a.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
 AND ((r.KIND='ARP' AND a.ELEMENT_TYPE='props'
                     AND a.METADATA_JSON:"name"::STRING=r.PROPERTY_NAME)
   OR (r.KIND='ARO' AND a.ELEMENT_TYPE='observations'
                     AND a.METADATA_JSON:"props"[0]:"name"::STRING=r.PROPERTY_NAME))
LEFT JOIN RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED.DIM_OSCAL_POAM_ELEMENT p
  ON r.KIND='POAM' AND p.SOURCE_RECORD_ID=r.CID
 AND p.SOURCE_SYSTEM_NAME='ARCHER'
 AND p.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
 AND p.ELEMENT_TYPE='poam-items'
 AND p.PK_DIM_OSCAL_POAM_ELEMENT_HASH=MD5_BINARY(CONCAT_WS('|',
    'v1_registry_path_instance','ARCHER','ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW',
    r.CID,'POAM','plan-of-action-and-milestones.poam-items[]',r.REF_ID))
ORDER BY r.N,r.CID,r.REF_ID;
