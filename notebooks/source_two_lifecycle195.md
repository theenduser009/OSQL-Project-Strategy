# Source Two lifecycle195 daily runner

Use [Cell7](source_two_lifecycle195_cell7.py) with its matching lifecycle195 CSV and runtime.

- From the accepted184 runtime, replace the matching CSV and Cells4,6,7.
- From lifecycle190, replace the matching CSV and Cell7. Cells1–6 stay the same.
- Preserve established source/model configuration, the separate Source One CSV and existing registry.

Start the first installation in a fresh session with Cell7 in PREVIEW. Run the seven cells once and inspect all four route results. No extra daily QA or guard cell is required.

Before a migration COMMIT, establish complete current-state Source records, one writer across both target pairs, required privileges including Catalog leaf DELETE, and a consistent recovery point for all four target tables. The runner does not attest full-record completeness or implement a shared writer lock.

Set Cell7 to COMMIT only after those deployment conditions and initial native PREVIEW are satisfied. Keep shared EXECUTE_WRITES disabled; the runner applies the approved policy in its copied route contexts. It internally previews all routes, transfers calculated exact approvals, then writes and verifies each route. Require COMMITTED_AND_VERIFIED with readback for every route.

Retirement is limited to the declared Source property leaves. Whole absent records and child records are preserved. Transactions are per route. Stop on partial or unknown outcomes and reconcile before retrying. Older code is not a data rollback after identity migration.

Cloud SQL adapter tests do not establish native Snowflake execution, production-scale performance or unattended deployment readiness. Save execution reports privately.
