# OSCAL Copy-and-Run Workbench

**Current query:** [Catalog metadata three-field QA](sql/CATALOG_METADATA_QA.sql).

Copy the complete query into a Snowflake DEV SQL worksheet and run it once.
The source RAW and persisted Catalog DIM paths are fully qualified; no table
placeholders or session variables need to be filled in.

It compares Source name, version and description with persisted Catalog metadata.
Return the three `FIELD_SUMMARY` rows. Up to 15 matched-ID status samples are
pseudonymous, and original identifiers/business text are not printed.
The query is SELECT-only and does not rerun notebook cells or write tables.
Current RAW may be newer than the persisted release; this is not acceptance
of an uncommitted mapper PREVIEW.

Runnable SQL is in `sql/`. The private OSCAL repository maintains the seven-cell
mapper, mapping CSVs and evidence. The Kobai folder was removed from this branch
at the owner's request; earlier Git commits may still contain its previous files.
