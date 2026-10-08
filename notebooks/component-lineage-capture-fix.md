# Component Lineage Capture Fix

This notebook cell addresses reference-collection lineage where the collection itself
is the mapped target and therefore has no scalar member target.

Run this cell after the mapper helper cell has been loaded and before rerunning PREVIEW.

```python
def _capture_contribution(contributions, row, target, context, origin=None):
    expected_target = _metadata_target(row)

    reference_root = (
        row.get("REPRESENTATION") == "references"
        and expected_target is None
        and target == ""
    )

    if (
        row.get("LINEAGE_REQUIRED_FLAG")
        and (target == expected_target or reference_root)
    ):
        contribution = {
            "source_field": row["SOURCE_FIELD_NAME"],
            "target": target,
            "origin": origin,
        }

        if contribution not in contributions:
            contributions.append(contribution)
```

After running the cell, rerun the SSP PREVIEW and then run
`notebooks/component-lineage-preview-check.md`.

Expected validation result:

```text
COMPONENT LINEAGE PREVIEW: PASS
MISSING_COMPONENT_LINEAGE = 0
STATUS = VERIFIED
```
