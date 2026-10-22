# OSCAL Copy-and-Run Workbench

**Current check:** [Source Two sprint PREVIEW value audit](qa/source_two_sprint_preview_value_qa.py).

This is Python for the same still-active Snowflake DEV notebook session after
the seven-cell mapper has completed PREVIEW. It compares the new mapped property
values with the retained source snapshots and reports Catalog statement omissions.

## Run once from Git

1. Open the current Python audit and copy its entire contents.
2. Add a separate Python Cell 8 after the seven mapper cells and paste the audit there.
3. Run only Cell 8 in the same active session. Leave Cells 1–7 unchanged;
   do not restart the session or rerun the mapper just to run this check.
4. Copy the audit summary and any reported exceptions back to the private mapping chat.

Cell 8 is a separate QA step; your maintained mapper still has seven runtime cells.
The audit reads the completed candidate and cached source inputs. It does not
rebuild the graph, read current RAW or persisted target tables, call the loader,
change the mappings or commit target changes. No downloads or uploads are needed.

If the session has restarted, the retained preview objects will be missing and
the script must stop. Do not treat a partial or missing-snapshot result as a pass.

The previously completed [Catalog group key-control QA](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql)
remains available for reference; do not repeat its accepted checks for this batch.

Mapper cells, mapping CSVs and registry definitions remain private. This public
repository contains QA tools only, with matching evidence in the private project
checkpoint. Do not post source record values, screenshots or credentials here.
