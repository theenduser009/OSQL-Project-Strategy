# Catalog Control Preview with Transform and TBD properties

This package contains 87 new field mappings. It adds the 13 Transform and 15 TBD rows to the earlier 59-field batch. Together with the existing Content ID property and one repeated worksheet row, the candidate covers 89 of the 90 named-property worksheet rows.

1. Replace `mapping.csv` and `routes_config.json` in the DEV notebook.
2. Replace Cells 3 and 4 with the two Python files in this folder. Use your current structural registry.
3. Run Cells 1–7 in DEV Preview. Target writes are disabled.

The date rules format recognized ISO dates and explicitly zoned timestamps while preserving the source offset and fractional seconds. Other timestamp values stay as JSON text and are counted in `NATIVE_CATALOG_TIMESTAMP_FALLBACK_OCCURRENCES`. The three sources for `published-date` are distinguished by their source field in the OSCAL property class. Tracking ID and the 15 TBD fields retain their supplied values as JSON text.

The earlier 59-field batch passed Snowflake DEV Preview. The expanded 87-field batch passed a local graph test and still needs its Snowflake DEV Preview.

Run `CHECK_CLIPPED_CATALOG_FIELD.sql` to verify the exact Archer key for worksheet row 125.
