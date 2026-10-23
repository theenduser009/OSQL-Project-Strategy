# OSCAL Copy-and-Run Workbench

## Current action — corrected Source Two eleven-field PREVIEW value QA

[Open the current read-only Python audit](qa/source_two_extensions_preview_value_qa.py).

The owner's four-route DEV PREVIEW passed. The first version of this audit
incorrectly combined Source and Topic fields sharing the name INFORMATION and
stopped with a contract mismatch. The corrected audit selects by original field
and compiled registry owner, then checks the exact target and lookup. No mapper
cell, mapping CSV or registry change is required. This independent audit checks the
new eleven extensions against the retained source records and candidate graph,
including original record ownership, duplicates and values swapped between
records. It also preserves the earlier child/Procedure/association checks.
It does not commit data, rebuild the mapper or query current RAW/target tables.

1. In the SAME still-active Snowflake session that completed PREVIEW, add one
   temporary Python QA cell after Cell7 (Cell8).
2. Replace the failed QA code with the entire corrected script and run ONLY
   that QA cell once.
   Leave mapper Cells1–7 unchanged.
3. Return the printed SOURCE_TWO_EXTENSIONS_PREVIEW_VALUE_QA report privately.
   The temporary QA cell may be removed after keeping its output.

If the required frozen session data is missing, the script stops. Do not replace
Cell7 or rerun the prior Cell9 commit adapter. No new COMMIT is authorized by
this audit or by publication. A later write needs a separately reviewed exact
delta and explicit approval.

The correction passed independent review and cloud checks: sixteen audit tests,
eleven actual-engine mapping/sample tests and six single-CSV checks, plus both
artifact verifiers. The new integration regression first reproduced the exact
contract mismatch against all 93 real compiled Catalog mappings, then passed
with this correction. Missing or duplicated intended mappings and wrong owner,
lookup or target paths still fail. These checks
do not establish a live value-QA PASS until the owner supplies its report.

## Artifact verification — operator tools

- [Approved-extension release verifier](qa/verify_source_two_bulk_extensions.py)
- [Historical four-file release verifier](qa/verify_source_two_daily_release.py)

These are engineer/CI utilities for already accessible private files, not code
to paste into a Snowflake notebook. They do not install files or authorize writes.
Source One and Source Two keep separate external mapping CSVs; runtime cells,
full mapping CSVs and registry definitions remain in the private project.
The owner takes the current Source Two CSV from private Mapping/ using the normal
process. A Git-to-notebook connection is not required.

## Completed historical checks — reference only

- [Earlier sprint value audit](qa/source_two_sprint_preview_value_qa.py):
  accepted for the older batch; its route counts do not match the new candidate.
- [Prior approved DEV commit adapter](run/09_APPROVED_DEV_COMMIT.py):
  already completed and verified. Do not rerun it.
- [Catalog group key-control SQL QA](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql).

Detailed evidence, exact proposed changes, branch recovery records and current
handoff stay in private Git. Raw records, photographs, business values and
credentials must not be posted here.
