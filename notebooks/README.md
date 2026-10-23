# Same-cell daily runner

## Inspect a fixed-policy mismatch

1. Replace only the existing final Python cell with the complete [Cell 7 Python file](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/notebooks/07_mapper_orchestrator.py). Keep Cells 1–6 and the persistent mapping files unchanged.
2. Keep `OSCAL_LOAD_MODE = "PREVIEW"`. If Cells 1–6 have already completed in the active session, run only Cell 7. After a session restart, run the unchanged Cells 1–6 first, then Cell 7 in PREVIEW.
3. Save the full printed `OSCAL_PIPELINE_REPORT` privately, including `daily_write_policy_diagnostics` if present.

Do not select COMMIT while the mismatch is unresolved. Do not add a helper cell, enter counts, change the approved policy hash, or repeat an already accepted value QA.

The diagnostic compares retained release/configuration/registry metadata. It reports hashes and structural key names, without printing their raw values. A mismatching policy still stops before graph construction or any target write; its combined check is not attributed to the last route. If the policy matches, PREVIEW can continue through ordinary no-write validation. This diagnostic update does not establish the cause of a live mismatch.

## Approved daily behavior after the binding is resolved

The already approved DEV policy permits validated INSERT/UPDATE for its fixed routes, release and destinations. Cell 7 builds and previews every route in the same invocation, transfers calculated counts to the existing loader guards, commits the same graphs and verifies readback. Retirements are blocked. No separate QA cell, retained preview session, saved receipt or manually entered counts is a daily dependency.

A successful write run reports `COMMITTED_AND_VERIFIED`. Stop on any error; do not blindly retry a failed or unknown commit. Transactions remain per route, so an earlier route can finish before a later route fails.

The policy does not authorize other sources, production destinations or scheduling. Disposable SQL-adapter cloud tests do not establish native Snowflake production readiness.
