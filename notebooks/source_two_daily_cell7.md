# Shared daily Cell 7

This generic runner selects PREVIEW or COMMIT, calls the shared pipeline, and prints its report. Use it with the matching private seven-cell package and its separate source CSVs.

From the accepted seven-cell cleanup package, replace Cells 1, 6 and 7 together. Cells 2–5, both persistent CSVs and the SQL registry are unchanged. A new Cell 7 with an older Cell 6 stops before writing.

Source and model selection remain explicit in Cell 1. COMMIT selects one separately approved route set; permissions from different route sets are never combined. The new single-source SSP scope permits inserts and updates without retirements. The existing four-route scope keeps its previously reviewed finite lifecycle permissions. Other model combinations remain PREVIEW-only unless separately authorized and tested.

For an approved direct COMMIT, start fresh, run Cells 1–6, then run Cell 7 in COMMIT mode. Shared EXECUTE_WRITES stays false; the pipeline manages the write configuration internally. No earlier manual PREVIEW, retained notebook state, manual counts or extra QA cell is required. The same invocation builds and validates its graphs, checks every selected route before the first write, and calculates the exact write envelopes automatically.

A successful write reports COMMITTED_AND_VERIFIED with matching readback for every selected route. Transactions remain per route; a later failure can leave earlier routes committed. Stop on errors, partial execution, unknown outcomes or failed post-commit readback; reconcile the full report before another run.

The SSP scope does not add property retirement or identity migration. Replacing or removing an already stored value-based property remains blocked by the existing obsolete-row check. Initial values and unchanged repeats use the existing idempotent loader.

Complete current-state input records, exclusive writer operation, appropriate target permissions and recoverable targets remain deployment prerequisites. Cloud tests do not establish native Snowflake compatibility or production-scale performance. Do not downgrade to older code after a committed identity migration.

[Open the matching Cell 7](source_two_daily_cell7.py).
