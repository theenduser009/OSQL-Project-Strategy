# Shared daily Cell7 — registry-based configuration

Use this runner only with the matching seven-cell registry-driven package. A Cell7-only replacement cannot upgrade older installations.

Configuration now comes from the existing element registry. Mapping CSVs still define field mappings, and the original registry rows still define OSCAL structure. The separate settings table is no longer read. An authorized administrator must first perform the controlled update to the existing registry: one nullable settings column and one configuration row containing the thirteen existing settings records. No new settings table is required.

Use all seven complete cells from the matched package when your installed version is uncertain. Keep the separate persistent mapping CSVs at their established locations; use the package's current SourceTwo CSV and the unchanged accepted SourceOne PPSM CSV. Select sources and models explicitly. Keep shared writes disabled in Cell1; choose PREVIEW or COMMIT in Cell7.

A fresh COMMIT does its own validation and planning before writing. It does not need a prior manual PREVIEW, retained session, manual counts, or an extra QA cell. Only the already authorized separate DEV write groups are supported. Combined, new source/model, Assessment Plan, Policies, and production writes are not enabled by this cleanup.

Before committing, use complete current input records, one target writer, the required existing target permissions, and recoverable targets. The daily role must have SELECT-only effective authority on the registry; its configuration is administered separately. Missing or malformed settings and mixed notebook versions stop before target work.

Require a COMMITTED_AND_VERIFIED result, successful readback for every selected route, and zero lineage gaps. Routes use separate transactions, so a later failure can follow an earlier commit. Stop on an error, partial result or unknown outcome and inspect the full report before any deliberate retry.

Cloud checks use synthetic inputs and disposable SQL. Native registry installation, effective grants, execution/readback, and measured performance remain deployment requirements. This runner adds no mapped fields or broader write/removal permissions, and does not request a repeat of an already accepted PPSM run.
