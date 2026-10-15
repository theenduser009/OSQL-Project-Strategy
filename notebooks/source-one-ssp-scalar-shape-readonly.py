# %% Source One SSP scalar-property shape investigation — READ ONLY
# 2026-10-15. Paste into ONE new Python cell in the EXISTING failing PREVIEW
# notebook session. Do NOT rerun Cells 1-7 or trigger COMMIT.
# Uses only the cached Source One selected source snapshot and compiled mapping.
# No SQL, registry writes, DIM/FACT writes, graph rebuild, or actual values/IDs printed.
from collections import Counter

_ROUTE = [c for c in MAPPING_CONTEXTS
          if c.get("source_key") == "source-one"
          and c.get("config", {}).get("OSCAL_MODEL") == "SSP"]
if len(_ROUTE) != 1:
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: expected exactly one Source One SSP route")
_ctx = _ROUTE[0]
_loaded = MAPPING_INPUTS.get("source-one", [])
if len(_loaded) != 168:
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: expected 168 loaded mapping records; found "
                       + str(len(_loaded)) + "; refresh CSV/compile PREVIEW only")
if _ctx.get("compiled_plan", {}).get("release") != "lean-csv-registry-v17-cia-null-lineage":
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: compiled mapper version not verified")
if _ctx.get("routing_report", {}).get("STATUS") != "READY":
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: compiled SSP route not ready")
if _ctx.get("config", {}).get("EXECUTE_WRITES") is not False:
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: shared write guard must remain disabled")
if tuple(SELECTED_MODELS) != ("SSP",):
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: select SSP alone, no other model")
_required_fields = {
    "AUTHORIZATION_PACKAGE_SUBMIT_DATE", "ATOIATO_EXPIRATION_DATE",
    "LEGACY_SAP_ID", "ALTERNATE_SYSTEM_ADMINISTRATOR_SA",
    "SYSTEM_ADMINISTRATOR_SA", "ENTITY", "BUSINESS",
    "ALLOCATE_BASELINE_CONTROLS", "ARCHIVE_CONTROLS",
    "FULL_CONTROL_ASSESSMENT_HELPER", "HELPER_ALLOCATED_CONTROLS",
    "_CURRENT_CONTROL_RISK_THRESHOLD", "_OF_SATISFIED_CONTROLS",
}
_selected = {r["SOURCE_FIELD_NAME"] for r in _ctx["mapping_rows"]}
if not _required_fields.issubset(_selected):
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: combined seven-field / Control Implementation compiled plan is stale")
_src = SOURCE_INPUTS.get("source-one", {}).get("source_df")
if _src is None or not hasattr(_src, "to_local_iterator"):
    raise RuntimeError("SSP_SHAPE_DIAGNOSTIC_STOP: frozen Source One snapshot is unavailable")

# Only the existing operators which call _oscal_property_values() directly.
_candidate_rules = []
for _rule in _ctx["mapping_rows"]:
    _path = _rule.get("OWNER_ELEMENT_PATH")
    _element = _ctx["compiled_plan"]["elements"].get(_path, {})
    _operator = _element.get("operator")
    if _rule.get("TRANSFORM_ID") != "skip" and _operator in ("properties", "observations", "values"):
        _candidate_rules.append((_rule, _operator))


def _safe_kind(_item):
    _item = _to_python(_item)
    if isinstance(_item, dict):
        return "OBJECT"
    if isinstance(_item, list):
        _kinds = {"OBJECT" if isinstance(_to_python(x), dict) else
                  "LIST" if isinstance(_to_python(x), list) else "SCALAR"
                  for x in _item}
        return "LIST_OF_" + "_AND_".join(sorted(_kinds or {"EMPTY"}))
    if _item is None:
        return "NULL"
    return type(_item).__name__.upper()


_issues = Counter()
_other_errors = Counter()
_examined = 0
for _record in _src.to_local_iterator():
    _doc = _metadata_parse(_record, _ctx)
    _examined += 1
    for _rule, _operator in _candidate_rules:
        if _rule.get("VALUE_SOURCE") == "CONFIG":
            continue
        _field = _rule["SOURCE_FIELD_NAME"]
        _raw = resolve_json_path(_doc, _field, default=SKIP_VALUE)
        if _raw is SKIP_VALUE or _raw is None or not _has_value(_raw):
            continue
        try:
            _mapped = _metadata_transform(_rule, _raw, _ctx)
            if _mapped is SKIP_VALUE or _mapped is None:
                continue
            if _operator == "values":
                _target = _rule.get("FIELD_RELATIVE_PATH")
                for _member in (_mapped if isinstance(_mapped, list) else [_mapped]):
                    _inner = _metadata_get(_member, _target) if isinstance(_member, dict) else _member
                    _oscal_property_values(_inner)
            else:
                _oscal_property_values(_mapped)
        except (TypeError, ValueError, ArithmeticError) as _error:
            _key = (_field, _rule["OWNER_ELEMENT_PATH"],
                    _rule["TRANSFORM_ID"], _safe_kind(_raw))
            if "Property value must be scalar" in str(_error):
                _issues[_key] += 1
            else:
                _other_errors[(_field, type(_error).__name__)] += 1

print("SOURCE_ONE_SSP_SCALAR_SHAPE_DIAGNOSTIC_READ_ONLY")
print("LOADED_MAPPING_RECORDS:", len(_loaded))
print("COMPILED_MAPPING_FINGERPRINT:", _ctx["compiled_plan"].get("mapping_fingerprint"))
print("SOURCE_RECORDS_CHECKED:", _examined)
print("SCALAR_SHAPE_ERROR_OCCURRENCES:", sum(_issues.values()))
for _key, _count in sorted(_issues.items(), key=lambda pair: (-pair[1], pair[0])):
    print("SCALAR_SHAPE_ERROR:", "FIELD=", _key[0],
          "OWNER_PATH=", _key[1], "TRANSFORM=", _key[2],
          "RAW_SHAPE=", _key[3], "RECORDS=", _count)
print("OTHER_TRANSFORM_ERROR_OCCURRENCES:", sum(_other_errors.values()))
for _key, _count in sorted(_other_errors.items(), key=lambda pair: (-pair[1], pair[0]))[:10]:
    print("OTHER_TRANSFORM_ERROR:", "FIELD=", _key[0],
          "EXCEPTION_TYPE=", _key[1], "RECORDS=", _count)
print("RESULT:", "REVIEW_SCALAR_FIELDS" if _issues else
      "NO_DIRECT_PROPERTY_SCALAR_OFFENDERS_FOUND_REVIEW_OTHER_OPERATORS")
print("NO SOURCE VALUES, CONTENT IDS, TARGET DML, OR COMMIT.")
