# OSCAL Validation and Notebook Examples

## Current Source Two same-cell daily runner

[Copy Cell 7](notebooks/07_mapper_orchestrator.py) · [Replacement instructions](notebooks/README.md)

The correction accepts the independently verified historical Assessment Results registry order under the fixed approved DEV policy. It retains the seven-cell daily flow, calculated count approval, validation, readback and blocked retirements. Follow the instructions for COMMIT in the existing Cell 7; a separate preview or QA cell is not a daily dependency.

## Release validation reference

[Current 184-rule frozen-preview validation](qa/source_two_owner_json184_preview_value_qa.py)

Run this only after PREVIEW of the matching 184-rule release, with selected
counts 151/7/10/16. [One-cell instructions](qa/source_two_owner_json184_preview_value_qa.md)
explain the temporary Cell 8 check; leave mapper Cells 1–7 unchanged.
This is a release check, not an extra daily ETL requirement. The audit reuses
bounded parsing and compact relationship summaries and prints phase progress.
Do not repeat an already accepted matching report just for this performance update.

Require result=PASS, error_count=0 and CHECKED for owner_json_properties,
default_record_permissions, native_information_criticality and scalar_array_properties. Save output privately.
This validates frozen values and ownership; it does not authorize or execute a
database commit. Permission JSON preservation is not OSCAL role creation or
access enforcement.

## Development candidate

[Six-field preservation candidate validation](qa/source_two_remaining190_preview_value_qa.md) includes a separate PREVIEW-only Cell 7 and its matching retained-value audit. It requires the matching candidate configuration; the accepted daily runner above remains unchanged.

## Earlier checks

These remain reference tools for their own releases:

- [Previous159 audit](qa/source_two_scalar_array159_preview_value_qa.py).
- [Previous153 audit](qa/source_two_native153_preview_value_qa.py).
- [Eleven-extension audit](qa/source_two_extensions_preview_value_qa.py).
- [Earlier sprint audit](qa/source_two_sprint_preview_value_qa.py).
- [Retained-metadata receipt](qa/retained_preview_review_guard.py).
- [Artifact verifier](qa/verify_source_two_bulk_extensions.py).
- [Historical multi-file verifier](qa/verify_source_two_daily_release.py).
- [Catalog group SQL check](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql).

Do not rerun accepted work to recover context or reuse an earlier commit approval.
Raw records, screenshots, identifiers and reports belong in your private workspace.
