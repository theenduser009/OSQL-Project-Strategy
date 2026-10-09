# %% Source Two Sub-Section BASE/STG column metadata inspection
# ONE new Python cell after earlier Source Two hierarchy diagnostic.
# SELECT-only; reads Snowflake INFORMATION_SCHEMA.COLUMNS, not business rows.
# No registry, mapper, DIM/FACT, or source data modifications.

import json
import re

if "session" not in globals() or "subsection" not in globals():
    raise RuntimeError("Use the same notebook session as the prior hierarchy check.")

parts = str(subsection).split(".")
safe = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
if len(parts) != 3 or not all(safe.fullmatch(part) for part in parts):
    raise RuntimeError("Previously resolved RAW identifier needs review.")
database, schema, raw_table = parts
if not raw_table.upper().endswith("_RAW"):
    raise RuntimeError("Previously resolved Sub-Section table must end with _RAW.")

stem = raw_table[:-len("_RAW")]
candidate_names = (stem, stem + "_STG")

def quote_sql(value):
    return "'" + str(value).replace("'", "''") + "'"

# INFORMATION_SCHEMA may expose case-sensitive physical column names, which
# are not safely replaced by a guessed business field alias.
sql = f"""
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION
FROM {database}.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = {quote_sql(schema.upper())}
  AND TABLE_NAME IN ({", ".join(quote_sql(n.upper()) for n in candidate_names)})
ORDER BY TABLE_NAME, ORDINAL_POSITION
"""
rows = [r.as_dict(recursive=True) for r in session.sql(sql).collect()]
by_table = {}
for row in rows:
    by_table.setdefault(str(row["TABLE_NAME"]).upper(), []).append(row)

def importance(column):
    name = str(column["COLUMN_NAME"])
    compact = re.sub(r"[^A-Z0-9]", "", name.upper())
    if compact == "CONTENTID":
        return 0
    if compact in ("REQUESTEDOBJECTID", "SOURCECONTENTID", "RECORDID",
                   "CONTENTIDENTIFIER"):
        return 1
    if "CONTENT" in compact and "ID" in compact:
        return 2
    if any(k in compact for k in ("OBJECTID", "RECORDID", "TRACKINGID")):
        return 3
    if compact == "ID" or compact.endswith("ID") or compact.endswith("KEY"):
        return 4
    return None

print("SOURCE TWO SUB-SECTION: BASE/STG ACTUAL COLUMN INVENTORY")
print("This is read-only column discovery, NOT a resolution of missing Content IDs.")
for role, name in (("BASE", candidate_names[0]), ("STG", candidate_names[1])):
    columns = by_table.get(name.upper(), [])
    matches = []
    variants = []
    for col in columns:
        metadata = {
            "name": col["COLUMN_NAME"],
            "type": col["DATA_TYPE"],
            "nullable": col["IS_NULLABLE"],
        }
        score = importance(col)
        if score is not None:
            matches.append((score, int(col["ORDINAL_POSITION"]), metadata))
        if str(col["DATA_TYPE"]).upper() in ("VARIANT", "OBJECT", "ARRAY"):
            variants.append(metadata)
    matches.sort(key=lambda item: (item[0], item[1]))
    print(json.dumps({
        "ROLE": role,
        "STATUS": "COLUMNS_FOUND" if columns else "NO_VISIBLE_COLUMNS",
        "COLUMN_COUNT": len(columns),
        "HAS_EXACT_CONTENT_ID": any(
            str(col["COLUMN_NAME"]).upper() == "CONTENT_ID" for col in columns
        ),
        "IDENTITY_NAME_CANDIDATES": [item[2] for item in matches[:40]],
        "IDENTITY_CANDIDATES_TRUNCATED": len(matches) > 40,
        "SEMI_STRUCTURED_COLUMNS": variants[:25],
        "SEMI_STRUCTURED_TRUNCATED": len(variants) > 25,
        "FIRST_COLUMN_NAMES": [col["COLUMN_NAME"] for col in columns[:25]],
        "FIRST_COLUMN_NAMES_TRUNCATED": len(columns) > 25,
    }, indent=2, default=str))

print("NO_IDENTITY_SELECTED: candidate column names do not establish business keys.")
print("NEXT: inspect the metadata output before attempting any source row join.")
print("DONE: one metadata SELECT only; no RAW/BASE/STG/DIM/FACT writes.")
