# OSCAL public copy-and-run workbench

**Current active step — October 14, 2026:** profile eight additional Authoritative Sources **Sub-Section scalar fields** in Snowflake DEV, as one read-only batch.

## Copy and run this one Python cell

[Open the current Source Two 8-field profiler](notebooks/source-two-subsection-next-eight-scalar-profile-readonly.py).

Open that link, copy the **entire Python file**, paste into **one new Python cell** of your connected Snowflake DEV notebook, and run only the new cell. Send the aggregate lines labeled `SOURCE_TWO_SUBSECTION_NEXT_8_SCALARS_READ_ONLY_PROFILE` back for review.

The script checks eight Source Two Sub-Section fields for missing/null values, text, numbers, timestamp text and resolved Archer selects. It discovers exactly one visible **DEV** RAW table and stops if the source scope is ambiguous. No credentials, private database/schema names, Archer record IDs, source payload values, or data samples are included or printed.

The script does **not** execute mapper Cells 1–7, create tables, run registry SQL, change mappings, or perform DIM/FACT writes or COMMIT. The eight mapping proposals are **GitHub-tested in the restricted OSCAL source-of-truth repository**, not yet Snowflake-previewed or approved for COMMIT.

## Repository boundaries

This public repo holds **only the current runnable and this short guide**. The previous two-field Sub-Section source profiler is complete and has been retired from the current branch; the historical file remains available through Git history. Keep all master mapping CSVs, regression tests, schema decisions, source records/screenshots, and full dated checkpoints in the **private OSCAL project repository**.

After reviewing this run's aggregate results, the next approved runnable will replace this script. Do not accumulate completed scripts on public `main`.
