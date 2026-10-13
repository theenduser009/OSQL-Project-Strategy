# %% Source Two — Control Standard ID/title semantic sample after populated-fields profiler
# READ ONLY. Run in the SAME Snowflake notebook session immediately after
# source-two-control-standards-populated-id-title-readonly.py.
# Reuses its validated target/source scope; no table rediscovery or writes.
import json

if not all(name in globals() for name in ("session", "references", "full_table", "target")):
    raise RuntimeError("Run the existing populated ID/title profiler first in this session.")
if not isinstance(references, list) or len(references) != 4:
    raise RuntimeError("Expected the four validated direct-reference SELECTs.")

fields = (
    "CONTROL_STANDARD_NAME",
    "STANDARD_ID",
    "ARCHER_STANDARD_ID",
    "STANDARD_NAME_ORIGINAL",
    "ARCHER_STANDARD_NAME",
    "CONTROL_STANDARD_REQUIREMENT",
    "ARCHER_CONTROL_STANDARD_STATEMENT",
)
columns = []
for field in fields:
    quoted = "'" + field + "'"
    value = "GET(t.CURATED_JSON, " + quoted + ")"
    expression = (
        "IFF(" + value + " IS NULL OR IS_NULL_VALUE(" + value + "), "
        "NULL, NULLIF(TRIM(" + value + "::VARCHAR), ''))"
    )
    if field.endswith("REQUIREMENT") or field.endswith("STATEMENT"):
        expression = "LEFT(" + expression + ", 130)"
    columns.append(expression + " AS " + field)

query = (
    "WITH reference_items AS (\n"
    + "\nUNION ALL\n".join(references)
    + "\n), ids AS (SELECT DISTINCT CONTROL_CONTENT_ID FROM reference_items)\n"
    + "SELECT t.CONTENT_ID::VARCHAR AS CONTENT_ID,\n    "
    + ",\n    ".join(columns)
    + "\nFROM " + full_table(target) + " t\n"
    + "JOIN ids r ON r.CONTROL_CONTENT_ID = t.CONTENT_ID::VARCHAR\n"
    + "ORDER BY t.CONTENT_ID::VARCHAR"
)
rows = [row.as_dict(recursive=True) for row in session.sql(query).collect()]
if not rows:
    raise RuntimeError("No referenced Control Standards returned; do not select a mapping.")

groups = {"BOTH_IDS": [], "STANDARD_ONLY": [], "ARCHER_ONLY": [], "NEITHER_ID": []}
for row in rows:
    a = row["STANDARD_ID"] is not None
    b = row["ARCHER_STANDARD_ID"] is not None
    key = "BOTH_IDS" if a and b else "STANDARD_ONLY" if a else "ARCHER_ONLY" if b else "NEITHER_ID"
    groups[key].append(row)

both_titles = [r for r in rows if r["STANDARD_NAME_ORIGINAL"] and r["ARCHER_STANDARD_NAME"]]
both_ids = groups["BOTH_IDS"]
report = {
    "REFERENCED_RECORDS": len(rows),
    "CONTROL_STANDARD_NAME_PRESENT": sum(r["CONTROL_STANDARD_NAME"] is not None for r in rows),
    "CONTROL_STANDARD_NAME_DISTINCT": len({r["CONTROL_STANDARD_NAME"] for r in rows if r["CONTROL_STANDARD_NAME"]}),
    "STANDARD_ID_PRESENT": sum(r["STANDARD_ID"] is not None for r in rows),
    "ARCHER_STANDARD_ID_PRESENT": sum(r["ARCHER_STANDARD_ID"] is not None for r in rows),
    "ID_FAMILY_RECORD_COUNTS": {k: len(v) for k, v in groups.items()},
    "ID_VALUES_DISAGREE_WHEN_BOTH_PRESENT": sum(r["STANDARD_ID"] != r["ARCHER_STANDARD_ID"] for r in both_ids),
    "STANDARD_NAME_ORIGINAL_PRESENT": sum(r["STANDARD_NAME_ORIGINAL"] is not None for r in rows),
    "ARCHER_STANDARD_NAME_PRESENT": sum(r["ARCHER_STANDARD_NAME"] is not None for r in rows),
    "TITLE_COVERED_BY_EITHER_FIELD": sum(bool(r["STANDARD_NAME_ORIGINAL"] or r["ARCHER_STANDARD_NAME"]) for r in rows),
    "TITLE_MISSING_FROM_BOTH_FIELDS": sum(not (r["STANDARD_NAME_ORIGINAL"] or r["ARCHER_STANDARD_NAME"]) for r in rows),
    "TITLE_VALUES_DISAGREE_WHEN_BOTH_PRESENT": sum(r["STANDARD_NAME_ORIGINAL"] != r["ARCHER_STANDARD_NAME"] for r in both_titles),
    "SAMPLE_ROWS": {
        group: subset[:3] for group, subset in groups.items()
    },
    "STATUS": "BUSINESS_ID_TITLE_SEMANTICS_PENDING_REVIEW",
}
print("SOURCE TWO: REFERENCED CONTROL STANDARD CANDIDATE PAIRS")
print(json.dumps(report, indent=2, default=str))
print("NO WRITES. Samples are source values for owner review, not approved OSCAL mappings.")
