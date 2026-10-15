# REVIEW CORRECTION 2026-10-15: status.state belongs to a separate
# SSP DIM element (status), not inside system-characteristics METADATA_JSON.
# For OPERATIONAL_STATUS=Decommissioned, expected status.state is 'disposition'.
# This read-only check displays ACTUAL stored values; it does not assert them.
# SOURCE ONE — ONE CONTENT ID: ACTUAL CURATED_JSON VS ACTUAL OSCAL DIM
# 2026-10-15 | Public copy-and-run code, read-only. NO SQL writes/COMMIT.
# Paste the complete file into ONE NEW Python cell in the active Snowflake notebook.
# No edits needed: auto-pick one Content ID with many populated fields.
# Optionally set CONTENT_ID_TO_CHECK to a specific Content ID string.
# Both sides show literal values; NO assumptions about transforms or equality.

import json as _sv_json
import re as _sv_re
import textwrap as _sv_wrap

CONTENT_ID_TO_CHECK = None  # None = automatically pick a well-populated record
FIELDS = (
    "POAMS", "AUTHORIZATION_PACKAGE_NAME", "ACRONYM",
    "OPERATIONAL_STATUS", "AUTHORIZATION_DECISION", "ATOIATO_DATE",
    "AUTHORIZATION_PACKAGE_SUBMIT_DATE", "ATOIATO_EXPIRATION_DATE",
    "WORKFLOW_STATUS", "INFORMATION_OWNER_IO", "AUTHORIZING_OFFICIAL_AO",
    "LEGACY_SAP_ID", "ALTERNATE_SYSTEM_ADMINISTRATOR_SA",
    "SYSTEM_ADMINISTRATOR_SA", "ENTITY", "BUSINESS",
)
_NO_VALUE = object()

def _object(x):
    if hasattr(x, "as_dict"):
        x = x.as_dict(recursive=True)
    if isinstance(x, str):
        try:
            return _sv_json.loads(x)
        except (ValueError, TypeError):
            return x
    return x

def _read_path(obj, tokens):
    for token in tokens:
        if not isinstance(obj, dict) or token not in obj:
            return _NO_VALUE
        obj = obj[token]
    return obj

def _source(obj, field):
    # Source One CURATED_JSON is keyed by the exact SQL_field_name.
    return obj.get(field, _NO_VALUE)

def _pretty(obj):
    if obj is _NO_VALUE:
        return "(NOT PRESENT)"
    try:
        s = _sv_json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        s = str(obj)
    # Wrap long text to avoid the notebook's horizontal output clipping.
    lines = []
    for line in s.splitlines() or [""]:
        if len(line) <= 105:
            lines.append(line)
        else:
            indent = len(line) - len(line.lstrip())
            lines.extend(_sv_wrap.wrap(line, width=105, subsequent_indent=" " * indent,
                                       break_long_words=True, break_on_hyphens=False))
    return "\n".join(lines)

# Existing retained source snapshot — no new RAW selection or notebook rerun.
frozen = SOURCE_INPUTS["source-one"]["source_df"]
chosen_id, chosen_obj, best = None, None, -1
for rec in frozen.to_local_iterator():
    cid = str(rec["SOURCE_RECORD_ID"])
    obj = _object(rec["CURATED_JSON"])
    if not isinstance(obj, dict):
        continue
    if CONTENT_ID_TO_CHECK is not None:
        if cid == str(CONTENT_ID_TO_CHECK):
            chosen_id, chosen_obj = cid, obj
            break
    else:
        populated = sum(_source(obj, f) not in (None, "", [], {}, _NO_VALUE)
                        for f in FIELDS)
        if populated > best:
            chosen_id, chosen_obj, best = cid, obj, populated
if chosen_obj is None:
    raise RuntimeError("Content ID unavailable in the frozen Source One snapshot.")

# Map the 16 screenshot fields to their current CSV paths, including the
# duplicate native SSP metadata-title destination (17 mapping occurrences).
loaded = MAPPING_INPUTS["source-one"]
rules = [r for r in loaded
         if r.get("SOURCE_FIELD_NAME") in FIELDS
         and r.get("SOURCE_KEY") == "source-one"
         and r.get("EXECUTION_STATUS") == "APPROVED"]
if len(rules) != 17 or len({r["SOURCE_FIELD_NAME"] for r in rules}) != 16:
    raise RuntimeError("Expected 16 source fields / 17 approved CSV mappings. "
                       "Check that the updated Source One CSV is loaded.")

# Read only the persisted DIM and FACT rows for this ONE Content ID. FACT is
# used to make sure 'props' is under the correct parent element.
sql_id = chosen_id.replace("'", "''")
data, query_errors = {}, {}
for model in ("SSP", "ASSESSMENT_RESULTS", "POAM"):
    binding = MODEL_CONTRACTS[model]["STORAGE_CONTRACT"]
    dim, fact, pk = [binding[k] for k in ("TARGET_DIM", "TARGET_FACT", "DIM_PK_COLUMN")]
    for name in (dim, fact, pk):
        if not _sv_re.fullmatch(r"[A-Z_][A-Z0-9_.]*", name):
            raise RuntimeError("Unexpected table/column identifier")
    query = f"""
      SELECT d.ELEMENT_TYPE AS KIND, d.METADATA_JSON AS VALUE_JSON,
             p.ELEMENT_TYPE AS PARENT_KIND
        FROM {dim} d
        LEFT JOIN {fact} e ON e.FK_TARGET_ELEMENT_HASH = d.{pk}
        LEFT JOIN {dim} p ON p.{pk} = e.FK_SOURCE_ELEMENT_HASH
       WHERE d.SOURCE_RECORD_ID = '{sql_id}'
         AND d.SOURCE_SYSTEM_NAME = 'ARCHER'
         AND d.SOURCE_TABLE_NAME = 'ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
         AND d.ELEMENT_TYPE IN ('props','system-characteristics','metadata',
                  'responsible-parties','parties','poam-items','results','status')
    """
    try:
        data[model] = [(str(r["KIND"]), str(r["PARENT_KIND"] or ""),
                        _object(r["VALUE_JSON"]))
                       for r in session.sql(query).to_local_iterator()]
    except Exception as ex:
        query_errors[model] = type(ex).__name__

def _oscal_value(row):
    path = row["OSCAL_ELEMENT_PATH"]
    model = ("SSP" if path.startswith("system-security-plan.")
             else "ASSESSMENT_RESULTS" if path.startswith("assessment-results.")
             else "POAM")
    if model in query_errors:
        return "(DIM QUERY ERROR: " + query_errors[model] + ")"
    items = data[model]
    field = row["SOURCE_FIELD_NAME"]
    matches = []
    if path.endswith("props[]"):
        parent = "results" if model == "ASSESSMENT_RESULTS" else "system-characteristics"
        prop_name = _sv_re.sub(r"[^a-z0-9]+", "-", field.lower()).strip("-")
        for kind, parent_kind, payload in items:
            if kind == "props" and parent_kind == parent and isinstance(payload, dict):
                if payload.get("name") == prop_name:
                    matches.append(payload.get("value", _NO_VALUE))
            # Some result properties may be embedded inside results METADATA_JSON.
            if model == "ASSESSMENT_RESULTS" and kind == "results" and isinstance(payload, dict):
                for prop in payload.get("props", []):
                    if isinstance(prop, dict) and prop.get("name") == prop_name:
                        matches.append(prop.get("value", _NO_VALUE))
    elif path.endswith("responsible-parties[]"):
        role = row.get("ROLE_ID")
        parties = {payload.get("uuid"):payload for kind, parent_kind, payload in items
                   if kind == "parties" and isinstance(payload, dict)}
        for kind, parent_kind, payload in items:
            if kind == "responsible-parties" and parent_kind == "metadata":
                if isinstance(payload,dict) and payload.get("role-id") == role:
                    matches.append({"assignment":payload,
                        "linked-parties":[parties[pid] for pid in payload.get("party-uuids",[])
                                          if pid in parties]})
    elif path.endswith("poam-items[]"):
        matches = [payload for kind, parent_kind, payload in items
                   if kind == "poam-items" and parent_kind == "plan-of-action-and-milestones"]
    else:
        # Status has its own DIM element. It is not nested in the
        # system-characteristics node's METADATA_JSON.
        if ".system-characteristics.status." in path:
            kind, parts = "status", path.split(".system-characteristics.status.",1)[1]
        elif ".system-characteristics." in path:
            kind, parts = "system-characteristics", path.split(".system-characteristics.",1)[1]
        elif ".metadata." in path:
            kind, parts = "metadata", path.split(".metadata.",1)[1]
        else:
            return "(UNSUPPORTED OSCAL PATH)"
        for item_kind, parent_kind, payload in items:
            if (item_kind == kind and isinstance(payload, dict)
                    and (kind != "status" or parent_kind == "system-characteristics")):
                value = _read_path(payload, parts.split("."))
                if value is not _NO_VALUE:
                    matches.append(value)
    return matches[0] if len(matches) == 1 else matches if matches else _NO_VALUE

print("=" * 74)
print("SOURCE ONE — EXACT VALUES IN CURATED_JSON AND PERSISTED OSCAL DIM")
print("CONTENT ID:", chosen_id)
print("Fields:", len(FIELDS), "| Mapping occurrences:", len(rules))
print("Auto-selected a record with many source values." if CONTENT_ID_TO_CHECK is None
      else "User-selected Content ID.")
print("This displays stored DIM values, NOT an uncommitted PREVIEW.")
print("=" * 74)

line_number = 0
for field in FIELDS:
    for row in [r for r in rules if r["SOURCE_FIELD_NAME"] == field]:
        line_number += 1
        print("\n" + "-" * 74)
        print(str(line_number) + ". FIELD:", field)
        print("OSCAL PATH:", row["OSCAL_ELEMENT_PATH"])
        print("CURATED_JSON ACTUAL VALUE:")
        print(_pretty(_source(chosen_obj, field)))
        print("OSCAL DIM ACTUAL VALUE:")
        print(_pretty(_oscal_value(row)))
print("\nEND. Read-only: no table writes, no COMMIT.")
print("If a new field has no persisted value, the failed COMMIT may explain it.")
