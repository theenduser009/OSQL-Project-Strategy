# Source Two same-cell daily runner

Copy the complete [Cell 7 Python file](https://github.com/theenduser009/OSQL-Project-Strategy/blob/main/notebooks/07_mapper_orchestrator.py) over the existing final Python cell of the matched Source Two notebook. Keep Cells 1–6, the persistent CSV and registry unchanged.

For the already approved four-route DEV daily INSERT/UPDATE policy:

1. Set `OSCAL_LOAD_MODE = "COMMIT"` in the replacement Cell 7.
2. If the matching Cells 1–6 are still loaded in this session, run only Cell 7. After a session restart, run Cells 1–6 once, then Cell 7.
3. Save the full printed `OSCAL_PIPELINE_REPORT` privately. Successful completion reports `COMMITTED_AND_VERIFIED`.

Cell 7 validates and previews every route within that invocation before any commit, transfers its calculated counts to the unchanged loader guards, commits the same graphs and verifies readback. No separate preview session, repeat value QA, additional cell, saved receipt or manually entered counts is required. Keep shared `EXECUTE_WRITES = False`.

The fixed policy accepts exactly the original registry contract and one independently reconstructed historical Assessment Results order variant whose graph/value/identity/lineage and disposable SQL behavior passed the equivalence gate. It cannot learn a new hash from the running notebook, accept a third order, or switch approved variants mid-run. Other route, mapping, registry semantics, identity or destination changes remain blocked. Retirements remain blocked.

Stop on any error. Do not blindly retry a failed or unknown commit: transactions remain per route, and an earlier route can finish before a later route fails. Keep `OSCAL_LOAD_MODE = "PREVIEW"` when only inspecting a proposed run without writes.

This approval covers the fixed Source Two DEV configuration, not other sources, production destinations or scheduling. Cloud SQL-adapter checks do not establish native Snowflake production readiness.
