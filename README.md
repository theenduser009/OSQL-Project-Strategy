# OSCAL Workbench

This public repository intentionally contains **only the currently needed copy-and-run script**. Completed/retired QA scripts have been archived privately for recovery.

## Current task — Control Standards ID reconciliation

Open [the current read-only Python cell](notebooks/source-two-control-standards-id-linkage-readonly.py) in a **connected Snowflake Python notebook**. Paste the complete script into one new cell and run **only that cell**.

The script first tries the active database/schema and any existing source profile. If those don't identify the required RAW tables, it uses Snowflake's accessible table metadata to locate one unambiguous matching namespace. It will stop without making changes if discovery is unavailable or ambiguous.

Share the `CONTROL_STANDARD_RAW_CANDIDATES`, `DIRECT_ID_MATCH_SUMMARY`, and `CONTROL_ID_TITLE_FIELD_CANDIDATES` output, or the candidates/error if it stops.

**Safety:** This is inspection only, not a mapper PREVIEW, registry setup, or DIM/FACT load. Do not run retired setup SQL or enable COMMIT to investigate a lookup error.
