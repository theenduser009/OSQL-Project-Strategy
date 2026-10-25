# Source Two lifecycle190 — Cell 7

[Open the complete Cell 7](source_two_lifecycle190_cell7.py).

Use this file only with the matched lifecycle190 seven-cell package and its persistent Source Two CSV. That package has204 data rows and190 selected rules:157 Catalog,7 Topic Assessment Results,10 Section Assessment Results and16 Sub-section Assessment Results. **This is not a Cell7-only upgrade from184:** matching Cells4 and6 are required. Obtain the matched package through the established private delivery.

1. Install the matched CSV and seven numbered cells in the existing notebook. Keep Source One separate.
2. For first installation, start a fresh session and run Cells1–7 with this Cell7's default `OSCAL_LOAD_MODE = "PREVIEW"`. Require `PREVIEW_COMPLETE` and all four route loads `PREVIEW_PASSED_NO_TARGET_DML`.
3. Before the first committed migration, establish complete current-state Source records, one writer, recoverable target state and native Snowflake acceptance. These are external requirements; cloud tests do not prove them.
4. For authorized daily DEV execution, use `OSCAL_LOAD_MODE = "COMMIT"` in this same Cell7 and run Cells1–7 once. Keep shared `EXECUTE_WRITES=False`. Cell7 internally previews every route and carries exact calculated approvals; no separate daily QA, retained-session approval, manual counts or extra commit cell.
5. Require `COMMITTED_AND_VERIFIED` with verified readback on all four routes. Save reports privately. Stop and reconcile any partial or unknown outcome before retry.

The fixed policy permits exact migration and removal only within its declared original-Source property families. Whole absent Source records and child/native-control deletion are excluded. Model routing is unchanged. The notebook has per-route transactions and no shared writer lock.

After a successful identity migration, do not rerun the old184 code against migrated targets. Recovery must reconcile data as well as code.

The existing [184 runner](07_mapper_orchestrator.py) remains available for its own matched release; do not mix the two. This delivery does not claim unattended production readiness or native Snowflake verification.
