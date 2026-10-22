# OSCAL Copy-and-Run Workbench

**Current query:** [Catalog group key-control value QA](sql/CATALOG_GROUP_KEY_CONTROL_QA.sql).

Copy the complete query into one Snowflake DEV SQL worksheet and run it once.
All source RAW and persisted Catalog DIM paths are fully qualified.

This checks the existing RELATED_TO_KEY_CONTROLS property at Topic, Section and
Sub-Section owners using original child identities. Return the three
`FIELD_SUMMARY` rows, including headers and every count column. Output is
aggregate counts only. The query is one read-only SELECT.

Zero is populated data. Empty source is distinguished from a missing required
property; decimal/double rendering is flagged for review rather than called an
exact match. Review all exception columns and observed source/target populations.
Current RAW may be newer than persisted DIM.

The previous completed Catalog metadata QA file was removed from current main
at the owner's request; its history and accepted results remain in the private
project checkpoint. Mapper cells, mapping CSVs and registry changes stay in the
private OSCAL repository. QA/validation copy-and-run scripts belong here, with
a corresponding private checkpoint. Do not publish source records or credentials.
