# OSCAL Copy-and-Run Workbench

## Current mapping batch

The eleven owner-approved Source Two extension mappings are implemented
privately and passed focused cloud checks. The existing115 rules are preserved;
the candidate selects126 rules from one partitioned external Source Two CSV.
Source One keeps its separate CSV. The existing SQL registry remains configured.

[Approved-extension artifact verifier](qa/verify_source_two_bulk_extensions.py)
is a read-only deployment/CI utility for an engineer who already has the private
candidate directory. It verifies the pinned seven cells, one external CSV,
source partitions and selected rule counts. **Do not paste this CLI utility
into a Snowflake notebook cell.** It does not install files, query Snowflake,
generate mapping data or authorize writes. Its exact code passed the private
cloud verification; the private runtime and CSV are not published here.

The owner's notebook is isolated and cannot connect to private Git. Interaction
is copy/paste-only. The permitted mechanism for replacing the persistent external
CSV is unverified; no upload/download/stage or temporary mapping generator is
assumed. Cloud checks do not establish Snowflake installation or daily scheduling.

The older [four-file package verifier](qa/verify_source_two_daily_release.py)
is retained as historical artifact QA. Its Git-import packaging is not the
owner's installation path. The former functional-development hold is resolved;
the owner resumed bulk development. Warehouse execution remains separate.

**Completed: the approved Source Two DEV commit was run by the owner and reported COMMITTED_AND_VERIFIED for all four routes, with storage verification passed and zero retirements. No repeat run is needed.**

The matched evidence and detailed receipt are recorded in the private project.
The scripts below are retained as reference for that completed candidate.
A new candidate requires a new preview and approval; do not reuse this fixed
approval as permission for another warehouse delta.

**Completed one-time delivery: [Approved DEV commit — Python Cell 9](run/09_APPROVED_DEV_COMMIT.py).**

The owner approved this exact scope after the DEV preview and value audit passed:
6,294 Catalog DIM updates, 128,063 child Assessment Results DIM inserts and
96,081 child FACT inserts, with no deletions/retirements.

## Historical delivery steps — already completed

1. Open the approved commit script and copy the **whole file**.
2. Add a new **Python Cell 9** after your existing mapper and QA cells.
3. Paste the code and run **only Cell 9 once**, in that same still-active session.
4. Return the printed SOURCE_TWO_SPRINT_COMMIT_REPORT in the private mapping chat.

**This script WRITES the exact approved DEV changes.** Leave Cells 1–8 unchanged.
No downloads/uploads, replacement of mapper cells, or further approval is needed
for this already-approved scope. Successful completion must report
COMMITTED_AND_VERIFIED; publication/tests alone do not establish warehouse success.

It calls the private mapper already loaded in the notebook. The seven runtime
cells, full mapping CSVs and registry definitions stay in the private project.
This public file is the one-time approved execution adapter, not the mapper engine.
It retains the existing mandatory approval guards and refuses changed
fingerprints, deltas or DEV destinations. Original preview globals stay intact.

Transactions are per route. On ANY error, stop and share the retained report;
a prior route may have committed. Do not blindly rerun this script or all routes.
The script blocks retry after a previous attempted commit in the same session.
A restarted session lacks the required frozen preview and QA evidence and must stop.

The exact adapter passed seven focused synthetic cloud tests privately. Public
delivery verification compiles and checks the artifact hash without running it.
No warehouse operation is executed by GitHub Actions.

## Completed/reference checks

- [Source Two PREVIEW value audit — Python Cell 8](qa/source_two_sprint_preview_value_qa.py)
- [Catalog group key-control SQL QA](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql)

Those owner checks are already accepted for this sprint; do not rerun them merely
to find the next step. Raw source records, screenshots, business values and
credentials must not be published here. Keep runtime/CSV/registry private and
record matching checkpoints in the private project.
