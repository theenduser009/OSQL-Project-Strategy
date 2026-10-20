# OSCAL — public copy-and-run workbench

## Current — October 20, 2026: verify Standard ↔ Procedure CR/RR pair parity

**One next step:** [Open the complete read-only Snowflake SQL](sql/source-two-control-standard-procedure-cr-rr-parity-readonly-2026-10-20.sql). Copy/paste the entire SQL into a **Snowflake DEV SQL worksheet**, run its final SELECT, and return screenshots of **all four result rows** (scroll horizontally to capture all result columns). No notebook Cells 1–7 need to be rerun.

This compares **two distinct original cross-reference / related-record pairs** verified from the owner's Archer relationship-definition screenshots:

- Control Standards **CR 30705** ↔ Control Procedures **RR 30704**.
- Control Procedures **CR 3088** ↔ Control Standards **RR 2497**.

The SQL derives the exact source `SQL_FIELD_NAME` from Archer metadata using **(LevelId, FieldId)**, resolves actual ContentIds in both RAW tables, checks field shapes/target integrity, measures originating-CR versus related-RR pair discrepancies **separately for each definition**, and measures cross-family overlap. It returns aggregates only—no business values or source IDs. This run inspects **all Control Standards and Control Procedures RAW rows**, rather than the earlier Source Two subset of 2,627 referenced procedures; do not expect subset counts to equal full-table counts.

**Evidence status:** The file is source-reviewed and GitHub read-back verified, but **not yet executed in Snowflake**. No native procedure links, cumulative mapping CSV, seven-cell mapper, or target DIM/FACT were modified. The current **104-row** private Source Two candidate has a prior accepted **PREVIEW** (44,669 proposed DIM / 44,521 proposed FACT, +124/+124 inserts, no writes); a newer 104-row COMMIT/readback is **not established** by the later read-only source screenshots. Historical 103-row and 30,566-DIM change COMMIT checkpoints concern earlier releases and do not prove the new relationship mapping.

**GitHub placement rule:** Standalone public-safe read-only SQL and diagnostic cells: **this public repository**. Authoritative executable notebook Cells 1–7, active CSV changes, implementation evidence/checkpoints: private [Oscal-mapping-strategy](https://github.com/theenduser009/Oscal-mapping-strategy) work branch. Never place client business records, screenshots, mapping runtime CSV or private notebook engine content in this public repo.

This step supersedes the **October 16 next-step instructions below**. They remain historical; do not repeat accepted loads or Back Matter profiling solely because they are still documented.

---

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
