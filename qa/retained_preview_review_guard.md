# Retained PREVIEW review

Run the Python script in one temporary Python cell in the same still-active notebook session that produced the successful PREVIEW and value QA. Leave the mapper cells and mapping files unchanged.

The script inspects retained report and compiled-context metadata only. It does not query tables, read DataFrames, rebuild graphs, rerun QA, create approval or execute writes.

It prints `RETAINED_PREVIEW_REVIEW_RECEIPT`. Keep the output private.

- `CAPTURED_REVIEW_REQUIRED_NO_WRITES`: current metadata was captured for review.
- `MATCHED_REVIEWED_PREVIEW_NO_WRITES`: metadata matches an optional separately supplied proposal.
- `REVIEW_REQUIRED_NO_WRITES`: inspect the bounded issue codes; do not retry a write.

Every result has `commit_authorized=false`. A previous QA PASS is reported as unbound because its older output did not record fingerprints. This receipt does not establish fresh warehouse state or document conformance. Do not change load mode based on this report alone.
