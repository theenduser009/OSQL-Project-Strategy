# OSCAL — public copy-and-run workbench

## Current — October 16, 2026: Source Two CATALOG Back Matter

The previous 30,566-DIM-update Catalog batch is **owner COMMITTED_AND_VERIFIED through existing Cell 7**. Do not rerun it, its old QA, or the separate commit-approval guard. The daily ETL stays on the same metadata-driven seven-cell pipeline, with dynamic pre-write validation and the same Cell 7 commit path.

### One next step: inspect the NEW Back Matter inputs together

**[Open the complete Back Matter input-structure Python cell](notebooks/source-two-catalog-back-matter-inputs-readonly.py).**

Repository: `theenduser009/OSQL-Project-Strategy`  
Branch: `main`  
Directory: `notebooks/`  
File: `source-two-catalog-back-matter-inputs-readonly.py`

1. Copy the complete file into ONE NEW Python cell in your existing Snowflake notebook `NB_ARCHER_OSCAL_MAPPER_V2`.
2. Run only that new cell. Do not rerun Cells 1–7, change the runtime mapping CSV, or COMMIT.
3. Return `CATALOG_BACK_MATTER_INPUTS` (status `CATALOG_BACK_MATTER_INPUT_STRUCTURE`).

This collects source member names/types/counts for Source `SOURCE_LINKS`, `TOPIC_REFERENCES` and `ATTACHMENTS`, plus `ATTACHMENTS` in Topic, Section and Sub-Section. It reads retained source frames only. It does not print URLs, record values or file contents; does not query target DIM/FACT; does not change mappings, configuration or registry; and does not arm a write guard. If retained frames are absent, it stops rather than reloading sources or repeating a completed COMMIT.

The earlier evidence established 62 Source records with link-object arrays, but not their member structure. Actual attachment content versus attachment references remains unresolved. This inspection is for new Back Matter mapping inputs, not another validation of the already committed fields. Syntax-shaped URL/base64 strings are not proof of reachable URLs or genuine attachment bytes. Source TOPIC_REFERENCES is inspected because its worksheet citation path and Extension Property label require reconciliation, not because it is automatically approved as a citation.

### Verification and code locations

The final exact script passed Python compilation and **12 local mock-frame tests**. Public source and private mirror have Git blob `443dabdf207054d02bf518dad97d21ecb4ca5bda`, read-back verified. It has not yet been executed in the owner's Snowflake environment. No new Back Matter runtime mappings have been activated.

Private mirror: `Oscal-mapping-strategy / simplify-metadata-boundary / notebooks/validation/READ_ONLY_SOURCE_TWO_BACK_MATTER_INPUTS_2026_10_16.py`.

[Private authoritative current status](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/CURRENT_STATUS.md) · [Dated Back Matter checkpoint](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/docs/checkpoints/2026-10-16-catalog-back-matter-inputs-standard-pipeline.md).

Finish Source Two CATALOG before Assessment Results or Component Definition. Prior native-control profiling/deferrals remain in the private checkpoint history and must not be repeated merely because an older public file exists.

### Historical scripts

Existing diagnostic files are retained for traceability, not instructions to rerun them. The complete previous README remains available [at immutable commit 81c65d8](https://github.com/theenduser009/OSQL-Project-Strategy/blob/81c65d87f303abc881432b3ff1446c4a79807ed3/README.md). Its guarded-COMMIT-next instructions are superseded by the owner's successful standard Cell 7 COMMIT and current pipeline decision.
