# OSCAL public copy-and-run workbench

**Current runnable, 2026-10-14:** corrected Source Two Sub-Section DIRECT `overview.prose` **DEV PREVIEW only**, no COMMIT.

## Required preparation in the existing Snowflake DEV notebook

1. From the **PRIVATE** OSCAL repository regular metadata-boundary branch, open the [corrected 62-rule Source Two CSV](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/release_candidates/2026-10-14-subsection-next-six-prose-direct/sources_source_runtime.csv). Download the exact file and replace the notebook File named `sources_source_runtime.csv`. Its 52 previously accepted rows are unchanged. Six new field candidates are enabled; four are deferred.
2. From the **PRIVATE** reviewed isolated branch, replace the code in original notebook **Cell 3** with [current Cell 3 mapping compiler](https://github.com/theenduser009/Oscal-mapping-strategy/blob/work/source-two-subsection-prose-direct-fidelity-2026-10-14/notebooks/staging/source-two-topic-only-2026-10-13/03_canonical_mapping_contract.py); then replace **Cell 4** with [current Cell 4 payload helpers](https://github.com/theenduser009/Oscal-mapping-strategy/blob/work/source-two-subsection-prose-direct-fidelity-2026-10-14/notebooks/staging/source-two-topic-only-2026-10-13/04_parsing_transform_payload_helpers.py). **Run only these two updated Python cells, in order.** They define/compile code but do not load DIM/FACT targets. Keep the existing cached source and registry snapshot; do not rerun Cell 2.
3. Copy the full [current public PREVIEW-only Python cell](notebooks/source-two-subsection-direct-prose-preview-only.py) into **one new Python cell** beneath the previously executed notebook. **Run only that NEW cell.** Its loader mode is hardcoded `PREVIEW`; no DIM/FACT target writes. The existing guarded PREVIEW may create/drop temporary tables.

**Do not rerun historical Cell 7** because its mode could still be `COMMIT`. Do not execute registry SQL, old accepted mapper cells, Source One scripts or a COMMIT.

## Why this PREVIEW changed

The earlier PREVIEW passed structural checks, but the independent original Archer `CURATED_JSON` QA found **1,085 Sub-Section descriptions with direct source prose differing from the stored candidate prose**. The generic scalar formatter stripped leading/trailing whitespace. The private staged mapper now supports opt-in `prose-direct` on the one new Sub-Section `overview.prose` mapping, preserving the original text exactly. The other five new fields and all existing Topic/Section mappings remain untouched.

The current PREVIEW runner supports either **52 accepted rows or a previously loaded 62-row six-field candidate** in memory, but verifies all 52 accepted rows remain identical, six new enabled/four deferred, exactly one Source Two CATALOG route, and no target DML. It should report `PREVIEW_RESULT: PASS_NO_TARGET_DML` with 33,679 DIM / 33,531 FACT, zero inserts and FACT updates. Actual DIM-update count is reported; old preview acceptance is superseded.

After the corrected PREVIEW passes, the next public runnable will be the updated *original Archer RAW versus native prose* field-value QA. No COMMIT is authorized yet. The original worksheet group-depth notation still requires mapping-owner confirmation.

## Publication boundary

This public repository hosts sanitized copy-and-run instructions only. Full mapping CSV, private helper code, tests, original payloads, reviews and dated checkpoints stay in the **private** OSCAL repository. The separate previously published `sql/change-control-dim-archer-trace.sql` is unrelated and remains untouched.

GitHub history retains previous runnable versions even when retired from the current public worktree.
