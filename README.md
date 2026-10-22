# OSCAL Copy-and-Run Workbench

Only current owner-run diagnostics live here. Obsolete notebooks, SQL scripts, and previous meeting documents have been removed from the working tree.

**Start here:** [Catalog metadata three-field QA](sql/CATALOG_METADATA_QA.sql).

Copy the SQL into Snowflake DEV, replace the **two table identifiers at the top** with the approved Source RAW and persisted Catalog DIM names, then run the full worksheet. The script does not write database tables. Its checks apply to the currently persisted target, not an uncommitted PREVIEW.

Runnable **SQL** goes in `sql/`; runnable **Snowflake notebook snippets** go in `notebooks/`. Executable mapper code, mapping CSVs, evidence and checkpoints remain in the private OSCAL repository.

**Security:** Files deleted from this working tree may remain in earlier public Git commits, forks, clones or caches. This cleanup is not a history purge. Remove or retire the repository separately when public distribution is no longer needed.
