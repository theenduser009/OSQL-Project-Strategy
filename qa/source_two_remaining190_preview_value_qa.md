# Six-field preservation candidate validation

This example is restricted to the matching 190-rule Source Two candidate. It does not replace the accepted daily release or authorize a commit.

The [candidate Cell 7](../notebooks/source_two_remaining190_preview_cell7.py) uses the existing six preceding cells and explicitly rejects COMMIT. Use it only with its matching candidate mapping configuration. A different release fails the audit's fixed fingerprint checks.

After a successful matching PREVIEW, the [value audit](source_two_remaining190_preview_value_qa.py) may run once in a temporary Python cell in the same session. It reads retained source and Catalog frames, comparing six new original-owner values and two existing properties with the same name. It checks duplicate properties, record ownership and parent relationships.

Require `SOURCE_TWO_REMAINING190_PREVIEW_VALUE_QA`, `result=PASS` and `error_count=0`. Save output privately. Missing session state or changed mapping contracts stop the audit. It does not query RAW or target tables, rebuild mappings, change approval or write data.

This is release validation, not an additional daily ETL cell. A PASS does not establish native-model completion, source alias equivalence or production lifecycle readiness. Do not rerun an accepted release for this candidate.
