# Same-cell daily runner

Copy the complete [Cell 7 Python file](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/notebooks/07_mapper_orchestrator.py) into the existing final Python cell of the matched notebook. Keep Cells 1–6 and the persistent mapping files unchanged.

The file defaults to `OSCAL_LOAD_MODE = "PREVIEW"`. For the already approved DEV daily INSERT/UPDATE policy, change that setting to `"COMMIT"` and run Cells 1–7 once in order. No separate preview session, QA cell, saved receipt or manually entered counts are required.

Cell 7 builds and previews every selected route, verifies the fixed release/destination policy, transfers the calculated counts to the existing loader guards, commits the same graphs and verifies readback. Retirements are blocked. A different route, release, execution contract or destination must stop rather than receive automatic approval.

A successful write run reports `COMMITTED_AND_VERIFIED`. Save the full pipeline report. Stop on any error; do not blindly retry a failed or unknown commit. Transactions remain per route, so an earlier route can finish before a later route fails.

The policy is limited to its approved DEV configuration. It does not authorize other sources, production destinations or scheduling. Disposable SQL-adapter cloud tests do not establish native Snowflake production readiness.
