# OSCAL — public copy-and-run workbench

**Current step, October 15, 2026:** Source Two Authoritative Sources — **next four Topic/Section Catalog property mappings, DEV PREVIEW ONLY**.

## First: replace the notebook CSV (no execution)

Download the [**private 67-row mapping review candidate**](https://github.com/theenduser009/Oscal-mapping-strategy/blob/simplify-metadata-boundary/Mapping/release_candidates/2026-10-15-topic-section-next-four/sources_source_runtime.csv) from the regular metadata-boundary branch. Use **Raw / Download** and replace the Snowflake Notebook Files entry named `sources_source_runtime.csv`. This file retains the prior **62 mapped-review rows exactly unchanged**, stages four new optional Topic/Section group properties and defers Section `INFORMATION`, which was null in all 10,566 records. The rolled-up Section criticality sum remains **diagnostic only** and is not activated.

**Do not rerun original Cells 1–7, registry setup, the last six-field Sub-Section COMMIT or the completed profile.** The previously accepted 62 mapping rows must remain loaded in the existing notebook Python session for the preflight comparison.

## Second: copy this one current PUBLIC Python runner

[**Open the next four Topic/Section no-write PREVIEW cell**](notebooks/source-two-topic-section-next-four-preview-only.py).

Copy the entire Python file into one **NEW Python cell** in the same active Snowflake DEV notebook session and run **only the new cell**. The runner compiles the private candidate against the cached Source Two snapshot and hardcodes the execution as `PREVIEW` even if historic `OSCAL_LOAD_MODE` is `COMMIT`.

The previous source profile reported 1,416 Topics and 10,566 Sections. `TOTAL_NUMBER_OF_SECTIONS` and `TOTAL_NUMBER_OF_SUB_SECTIONS` were numeric; `SECTION_SHORT_DESCRIPTION` was source text with 1,965 HTML-like values. The photo clipped the far-right type decision for `DOCUMENT_NUMBER`, so the new runner checks its actual 1,416 cached values: **1,403 JSON NULL and exactly 13 nonblank strings** before compiling or previewing. Anything else **stops without target DML**.

**Expected PREVIEW envelope (subject to actual DEV readback):** 33,679 DIM / 33,531 FACT graph identities, **0 DIM/FACT inserts**, **11,982 DIM payload updates** across Topic+Section groups, **0 FACT updates** and 21,697 unchanged DIM. No physical target writes or COMMIT. The remaining four field/source-to-exact-property value checks and owner approval of clipped source worksheet paths are separate gates after PREVIEW.

Output begins `SOURCE_TWO_NEXT_FOUR_TOPIC_SECTION_CATALOG_PREVIEW` and should end `RESULT: PREVIEW_PASSED_NO_TARGET_DML; NEW_FOUR_FIELD_QA_PENDING`. If it says `SOURCE_TWO_TOPIC_SECTION_PREVIEW_BLOCKED_...` send the exact error; do not rerun old COMMIT cells.

## Repository boundaries

This public workbench holds only the current sanitized Python runnable, README, and previously requested unrelated `sql/change-control-dim-archer-trace.sql`. The completed Topic/Section source profiler was retired from the current worktree; it remains recoverable in Git history. Full CSVs, mapping decisions, tests, and client details stay in the PRIVATE OSCAL project repo.

**No DIM/FACT source writes or COMMIT are performed by this PREVIEW.**
