# Shared daily Cell 7

This is the generic runner for the matched seven-cell cleanup release. It selects PREVIEW or COMMIT, calls the shared pipeline, and prints the report.

Use it with the matching configuration, compiler, transformations and loader from your private deployment package. A new Cell 7 with an older Cell 6 stops before writing.

From the matched lifecycle195 installation, replace existing Cells 1, 3, 4, 6 and 7. Cells 2 and 5 and the persistent mapping CSV are unchanged. Do not add another permanent cell. Keep the separate source CSVs and existing registry.

For initial acceptance of the trimmed package, start a fresh DEV session and run Cells 1–7 in PREVIEW. Save the full Cell 7 report privately. No separate daily QA cell or manual change counts are required.

COMMIT remains limited to the existing approved four-route DEV policy. It validates all routes before the first write and calculates the exact write envelopes within the same invocation. Transactions are per route; a later failure can leave earlier routes committed. Do not blindly retry an unknown or partial outcome.

Complete current-state input records, exclusive writer operation, appropriate target permissions and recoverable targets remain deployment prerequisites. Cloud tests do not establish native Snowflake compatibility or production-scale performance.

The previous lifecycle195 runner remains available with its original package. Do not mix release files or downgrade code after a committed identity migration.


[Open the matching Cell 7](source_two_daily_cell7.py). Replace it only as part of the matched private package described above.
