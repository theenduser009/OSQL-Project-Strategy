# OSCAL Validation

[Current frozen-preview value validation](qa/source_two_native153_preview_value_qa.py)

After a successful PREVIEW of the matching153-rule release, add one temporary
Python Cell8 in the same active notebook session. Paste the entire validation
script and run only Cell8. Leave Cells1–7 unchanged.

The report prints underneath the cell, with marker
`SOURCE_TWO_NATIVE153_PREVIEW_VALUE_QA`. The current release requires selected
rule counts120/7/10/16, `result=PASS`, `error_count=0`, and
`native_information_criticality.status=CHECKED`. Save the complete output
privately. The validator also supports older releases; `NOT_ENABLED` does not
validate the current additions. Missing session state or a failed check stops
execution.

This script reads the frozen preview; it does not authorize or execute a
database commit. Raw records, screenshots, identifiers and reports belong in
your private workspace.

## Earlier checks

These remain reference tools for their own accepted releases:

- [Eleven-extension audit](qa/source_two_extensions_preview_value_qa.py).
- [Earlier sprint audit](qa/source_two_sprint_preview_value_qa.py).
- [Artifact verifier](qa/verify_source_two_bulk_extensions.py).
- [Historical multi-file verifier](qa/verify_source_two_daily_release.py).
- [Catalog group SQL check](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql).

The historical commit adapter has already been used. Do not rerun it for a new
release or reuse an earlier approval.
