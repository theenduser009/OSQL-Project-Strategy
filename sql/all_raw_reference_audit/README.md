# Read-only audit of Archer RAW record references

## Run these two files in Snowflake DEV

1. [01_RAW_TABLE_INVENTORY.sql](01_RAW_TABLE_INVENTORY.sql) lists the actual visible ARCHER_CONTENT_*_RAW objects in RTX_RAW_DEV.ES_ESC_GRC and their required columns. Compare the names/count with your Matillion loader's expected44-table inventory. The SQL does not assume that discovering any44 objects proves they are the expected44.
2. [02_ALL_RAW_STRUCTURED_REFERENCE_AUDIT.sql](02_ALL_RAW_STRUCTURED_REFERENCE_AUDIT.sql) runs one complete anonymous block. Select the entire file and run it as one statement. Its default SUMMARY mode reports each table/field/status; change only v_report_mode from SUMMARY to DETAIL to get each candidate reference's owner ID, JSON path, array index and target-table result.

Neither script updates RAW/curated data, OSCAL DIM/FACT, registry or metadata. No temp tables or stored procedures are created. The assistant has not compiled or executed these scripts in Snowflake; source review is separate from native validation. This is an audit, not the proposed enrichment UPDATE.

## What it checks

The target index comes from each observed RAW_DATA.RequestedObject.Id and RequestedObject.LevelId, not from guessed table names or an assumption that every stored CONTENT_ID is an Archer ID. Stored CONTENT_ID is retained as a separate diagnostic value; a difference can be a historical tracking/UUID convention and is not automatically an invalid Archer reference.

RAW_DATA and CURATED_JSON are normalized once when they contain JSON text. All RAW array envelopes are inspected. One physical SQL row with multiple RAW envelopes is reported as unverified curated ownership; its single CURATED_JSON is not assigned to every referenced owner. Duplicate envelopes within one physical row do not invent extra target rows; duplicate physical target rows remain ambiguous.

Structured objects are discovered at every depth of original curated fields, including direct object fields and arrays. Objects with either ContentId or LevelId key remain visible, including null/invalid/incomplete objects. The known derived _OSCAL_RESOLVED_RECORD_REFERENCES sidecar is excluded from this source discovery. Numeric-only arrays are NOT inferred to be Archer references: they need a separate declared field/target contract and are outside this structured-object denominator.

Target matching uses the exact pair (raw Archer LevelId, raw Archer ContentId), a single physical target row/table, a singleton valid target envelope and OBJECT curated JSON. ARCHER_META_LEVEL must identify the level uniquely. No universal business-name field is invented or required just to establish record/JSON existence.

## Read the results correctly

- Every visible matching metadata table appears in SUMMARY, including missing/ambiguous canonical columns, empty tables and unusable curated/raw identities.
- SOURCE_AUDIT_STATUS must be checked separately from reference counts. A zero reference count with unusable JSON or missing columns is not a coverage pass.
- UNIQUE_CURATED_TARGET_FOUND proves an exact one-hop source-record lookup in this snapshot. It does not prove enrichment was written, business-name/value mapping completed, or an OSCAL relationship exists.
- ENRICHMENT_STATUS reports whether the original field has a sidecar entry. FIELD_PRESENT_NOT_VALIDATED is deliberately not an enrichment-success assertion; stale values still require parity checking.
- Ambiguous matches report their actual TARGET_TABLES/physical-row counts; REPRESENTATIVE_TARGET_RAW_TABLE / REPRESENTATIVE_TARGET_TABLES show representative table names, not an exhaustive list.
- SUMMARY groups every discovered candidate occurrence into one REFERENCE_STATUS. DETAIL lists all occurrences without a LIMIT. SOURCE_ROW_NO is an audit-local physical-row ordinal, not a persistent key.
- Keep counts based on REFERENCE_OCCURRENCES. The repeated SOURCE_PHYSICAL_ROWS/table metrics are informational and must not be summed over field/status rows.
- To claim complete structured-reference coverage, reconcile all discovered occurrences, require the expected table inventory, no unreadable/missing/unusable source coverage, and no unresolved/ambiguous/invalid required references. Incomplete objects may need classification rather than automatic treatment as confirmed links.
- Only objects visible to the executing role can be discovered. A SELECT privilege error stops the audit; it is not silently skipped. The full audit reads the matching RAW datasets; no production run/performance claim is made.

The existing enrichment UPDATE recognizes only8 field contracts and levels5/39 and skips an entire record when any reserved sidecar key exists. This audit has no such field whitelist or whole-sidecar skip.

## SQL source references

- [Snowflake dynamic RESULTSET / RETURN TABLE](https://docs.snowflake.com/en/developer-guide/snowflake-scripting/resultsets)
- [Anonymous block with EXECUTE IMMEDIATE](https://docs.snowflake.com/en/sql-reference/sql/execute-immediate)
- [Recursive FLATTEN](https://docs.snowflake.com/en/sql-reference/functions/flatten)

No actual source record values or query results are included in this public repository.
