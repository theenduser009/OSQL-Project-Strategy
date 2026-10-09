# OSCAL workbench — current runnable only

The public repository is intentionally limited to one safe, current copy-and-run script. Earlier scripts and SQL remain archived in the private OSCAL repository.

## Current Source Two task: identify populated Control Standard ID and title fields

1. Open [the read-only Python cell](notebooks/source-two-control-standards-populated-id-title-readonly.py).
2. Copy it into **one new Python cell** in your connected Snowflake notebook and run **only that cell**.
3. Share the `CANDIDATE_COUNTS` output, particularly `FIELD_NAME`, `VALUE_TYPE`, `NONEMPTY_SCALAR_RECORDS`, and `DISTINCT_NONEMPTY_SCALAR_VALUES`.

This checks *nonempty values*, not only whether the source JSON contains a field name. It does not update tables, load OSCAL controls, or issue registry changes.
