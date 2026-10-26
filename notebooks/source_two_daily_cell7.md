# Shared daily Cell 7

The runner selects PREVIEW or COMMIT, invokes the shared pipeline and prints its report. Use it with the matching metadata-driven seven-cell package and separate source mapping CSVs.

Install and verify the administered metadata table before running the new package. The runtime role needs SELECT-only access to that table and its existing source, registry and target privileges. Source/model profiles, defaults, field contracts and write permissions are data; a mapping row cannot authorize a destination or deletion.

For the upgrade from the preceding fingerprint-based shared package, replace complete Cells 1, 3, 4, 6 and 7 together. Cells 2 and 5, both persistent mapping CSVs and the hierarchy registry are unchanged. Do not install this runner alone. A mixed runner/loader version stops before writing.

Source and model selection remain explicit in Cell 1. An automatic COMMIT must exactly match one enabled administrative write group. Permissions from different groups are never combined. This upgrade does not add a group, target, operation or retirement permission. Other selections remain PREVIEW-only unless separately configured, authorized and tested.

After metadata setup, run Cells 1–6 in a fresh session, select the mode in Cell 7 and run it. Keep shared EXECUTE_WRITES false; the pipeline manages write configuration internally. COMMIT performs its own all-route preflight and calculates fresh exact envelopes in that invocation. No separate manual PREVIEW, retained preview session, manual counts or extra QA cell is required.

Successful writes report COMMITTED_AND_VERIFIED with matching readback for every selected route. Transactions remain per route, so a later failure can leave an earlier route committed. Stop on an error, partial result, unknown outcome or failed readback; reconcile the full report before retrying.

The existing finite property lifecycle is unchanged. Missing whole input records grant no deletion permission. Changed or removed value-keyed properties without an approved lifecycle remain blocked. Complete current records, exclusive writer operation, effective privileges and recoverable targets remain deployment prerequisites.

Cloud tests verify disposable transports and the actual notebook paths. They do not establish native metadata setup, effective account grants, native runtime acceptance or production-scale performance. Do not downgrade to code with old identities after a committed identity migration.

[Open Cell 7](source_two_daily_cell7.py).
