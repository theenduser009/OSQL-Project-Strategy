# Component Lineage Capture Fix

## Permanent placement

This function belongs in **Cell 4 — parsing / transform / payload helpers**.

Replace the existing `_capture_contribution()` function in Cell 4. It should remain
between `_oscal_prop()` and `_assign_mapped()`.

It is **not** an eighth mapper cell.

The standalone cell below can still be used as a temporary session override when Cell 4
has already been executed. For future notebook runs, keep the corrected function directly
inside Cell 4 so the fix is loaded normally with the seven-cell mapper.

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
