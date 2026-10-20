# OSCAL — public copy-and-run workbench

## Next — October 20, 2026: owner Procedure mapping correctness (one read-only run)

**New accepted DEV readback:** The owner's single-row persisted Catalog Control DIM check returned **10,422** native Control nodes, **0** invalid `archer-content-id` prop identities, **0** duplicate Catalog+Standard identities, **38,311** in-scope distinct global Standard→Procedure pairs, and **410,598** distinct *Catalog-scoped* Standard→Procedure associations anchored to **6,294 native controls across 24 Catalogs**. These results confirm persisted target identity only. **No new Procedure link or 104-row mapping COMMIT was performed by that query.**

**One next step:** [Open Source Two owner-level Procedure vs Standard-closure read-only SQL](sql/source-two-catalog-owner-procedure-versus-standard-closure-2026-10-20.sql). Paste the whole query into a Snowflake DEV worksheet; return its **five aggregate result rows**, scrolling horizontally to show `PAIRS_PRESENT_IN_BOTH`, `PAIRS_ONLY_EXPLICIT_OWNER`, and `PAIRS_ONLY_STANDARD_IMPLIED`.

**Why this one matters:** the original four Catalog worksheet field occurrences are direct owner-level `RELATED_CONTROL_PROCEDURES` (303,983 reference occurrences). The separate, newly verified Standard-origin Archer CR30705 relationship generates **1,974,800 owner–Standard–Procedure association instances** when joined through *direct owner `CONTROL_STANDARDS`*. An exact pair-level comparison—not a row-count comparison—must determine whether those two distinct Archer relationship families agree for each owner before mapping an owner-level field to native control links. Do not fan out any Procedures to all Standards in the same Source/Group.

The query is **SELECT only**, reads no OSCAL DIM/FACT, emits no original IDs or confidential values, and does not run Cells 1–7. It was source-reviewed and GitHub read-back verified, **but has not been owner-executed**. The prior 38,460 CR/RR parity, 38,311 direct-owner scope, and 10,422 persisted control checks are **complete**; do not rerun them unless inputs changed.

In private `Oscal-mapping-strategy`, an **eight-row REVIEW-ONLY relationship matrix** now explicitly separates the four owner Procedure fields from Standard CR30705/Procedure RR30704 and the independent Procedure CR3088/Standard RR2497 family. It is NOT the 104-row runtime CSV and changes no mapping status or warehouse data. Native links need a real resolvable URI/resource; optional custom OSCAL properties require a verified Archer stable field GUID and namespace per the October 20 meeting direction. Neither option has yet been approved as an active payload.

The earlier "persisted control anchor" step below is **completed** and is superseded as an instruction.

---

## Latest — October 20, 2026: native Catalog control anchor check (one run)

**Owner DEV read-only results from the prior Source Two scope query are accepted:** **38,311 distinct** Standard→Procedure pairs are attached to Standards directly referenced at Source, Topic, Section, or Sub-Section. **149** distinct pairs are outside that owner scope; the two counts reconcile to the previously bidirectionally verified **38,460** full-RAW pairs. All **39,897** direct Source Two Standard reference occurrences had valid positive numeric IDs; there are **1,606** distinct Standards in this scope, of which **640** have Procedure pairs, spanning **2,627** distinct Procedures. The **1,974,800** owner–Standard–Procedure association instances are NOT new native OSCAL links; do not fan out owner-level references.

**One next run, SQL worksheet in Snowflake DEV:** [Open the full native Catalog control anchor diagnostic](sql/source-two-catalog-persisted-control-procedure-anchor-readonly-2026-10-20.sql). Paste/run the whole SELECT. Return a screenshot of its **single result row**, scrolling horizontally to include all columns.

This checks whether the verified source-side Standard–Procedure pairs actually belong to a **persisted** native Catalog Control DIM node, using the exact current private seven-cell identity convention (`Catalog SOURCE_RECORD_ID` + `controls[]` node + `props[name='archer-content-id']`). It reports valid and invalid node identity properties, duplicate logical Catalog+Standard keys, distinct global pairs supported by persisted controls, and per-Catalog associations. **This is not a request to rerun notebook Cells 1–7, COMMIT, or repeat the accepted 38,460 / 38,311 read-only tests.**

NIST OSCAL 1.2.3 does **not** permit invented procedure `link.href` values: a native link needs a valid URI target, and an internal `#uuid` back-matter target needs an actual back-matter resource with linked/embedded content (rlink/base64). Verify an approved real reference or select a legitimate extension representation; do not invent it or clone 1,974,800 owner associations into DIM.

**Provenance:** The link-anchor SQL is published and GitHub read-back verified, but **has not run in Snowflake**. The owner screenshots establish only **current source-to-target reference scope**. The 104-row private cumulative CATALOG candidate is evidenced as prior **PREVIEW** (+124/+124 prospective inserts), not a newly committed revision. Existing private mapping CSV, loader, registry, deterministic keys, and target DIM/FACT were untouched.

The earlier owner-scope and CR/RR parity runs in sections below are **completed checks, not the next step**. Keep historical results but do not repeat accepted unchanged work.

---

## Next — October 20, 2026: which validated Procedure pairs belong in Source Two CATALOG?

The owner's DEV read-only CR/RR parity screenshot **verified 38,460/38,460 Control Standard → Control Procedure pairs** between `Level41 CR 30705` and `Level39 RR 30704` with zero pair-only discrepancies, invalid IDs, missing RAW targets, or duplicate target IDs. The **555** Procedure CR3088 pairs are all contained in the first family. Standard RR2497 is **not resolvable** from `ARCHER_META_FIELD` using (LevelId41, FieldId2497), so its zero-item output and 555 apparent CR-only pairs **cannot** be treated as a failed reverse match. The second Archer family stays on hold.

**One next step:** [Open the read-only Source Two Catalog direct-owner scope SQL](sql/source-two-catalog-standard-procedure-scope-readonly-2026-10-20.sql). Run that whole query once in a **Snowflake DEV SQL worksheet**. It returns only **six aggregate rows**, grouped by Source, Topic, Section, Sub-Section, ALL Source Two direct owners, and Standards outside that owner scope.

The query uses the four approved direct `CONTROL_STANDARDS` owner fields from Source Two and the independently verified target Standard CR `RELATED_CONTROL_PROCEDURES`. It reports how much of the confirmed 38,460-pair relationship can possibly attach to actual selected native Catalog controls, **without** joining every Section/Group Procedure to every control. It avoids returning any original ContentId or source business text.

Send one screenshot with **all six rows and their columns** (horizontal scroll as needed). Per-level counts can overlap and must not be added as distinct pairs. All-scope + outside-scope distinct pair counts should total 38,460 if the RAW snapshot is unchanged. This is only a scoped mapping candidate gate: it does not prove final per-Catalog graph identity, a valid OSCAL `link.href`, native link representation, or COMMIT.

**Release boundary:** The file is GitHub-published and source reviewed for SELECT-only intent, but has **not run in owner Snowflake**. No private seven-cell mapper changes, runtime CSV changes, DIM/FACT writes, link additions or new COMMIT are claimed. Source Two 104-row catalog candidate remains separate prior **PREVIEW** evidence only. Standalone diagnostics remain in this **public** OSQL workbench; executable mapper/CSV stays private.

The previous Standard/Procedure parity-run instructions below are **completed evidence**. Do not rerun them unless underlying RAW or metadata has changed.

---

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
