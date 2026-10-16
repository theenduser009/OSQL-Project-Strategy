# %% Source Two CATALOG routing cause — one READ-ONLY Python cell
# Execute in the SAME NB_ARCHER_OSCAL_MAPPER_V2 session after failed Cell 7.
# Inspects the existing Cell 1/2/3 variables ONLY. No source read, graph
# regeneration, SQL, target writes, COMMIT or extra pipeline run.
import hashlib
from collections import Counter

print("SOURCE_TWO_CATALOG_MAPPING_ROUTE_READ_ONLY")
print("SELECTED_MODELS:", tuple(SELECTED_MODELS))
for _p in SOURCE_PROFILES:
    if "CATALOG" not in _p.get("MODEL_KEYS", ()):
        continue
    print("SOURCE_KEY:", _p["SOURCE_KEY"])
    print("MAPPING_FILENAME:", _p.get("MAPPING_FILE"))
    _rows = MAPPING_INPUTS.get(_p["SOURCE_KEY"], [])
    print("CACHED_MAPPING_INPUT_ROWS:", len(_rows))
    print("CACHED_EXECUTION_STATUSES:",
          dict(Counter(str(r.get("EXECUTION_STATUS") or "") for r in _rows)))
    try:
        with open(_p["MAPPING_FILE"], "rb") as _f:
            _bytes = _f.read()
        _blob = hashlib.sha1(
            ("blob %d\0" % len(_bytes)).encode("ascii") + _bytes
        ).hexdigest()
        print("NOTEBOOK_FILE_GIT_BLOB:", _blob)
        print("NOTEBOOK_FILE_VERSION:",
              "REVIEWED_67_ROW_FOUR_FIELD_CANDIDATE" if _blob ==
              "6d46ab5f1448b7565dfac4f0ef14adfbc34e6f12" else
              "OLDER_26_ROW_REVIEW_CSV" if _blob ==
              "2eeb0233c40b2ed7bbac4acf8db1f494b57de7ba" else
              "OTHER_BYTES_CHECK_CACHED_ROUTE_REPORT")
    except OSError:
        print("NOTEBOOK_FILE_VERSION: FILE_NOT_ACCESSIBLE")
    for _context in MAPPING_CONTEXTS:
        if (_context.get("source_key"),
            _context.get("config", {}).get("OSCAL_MODEL")) != (
                _p["SOURCE_KEY"], "CATALOG"):
            continue
        _report = _context["routing_report"]
        print("ROUTE_STATUS:", _report.get("STATUS"))
        for _name in ("INPUT_ROWS", "SELECTED_ROWS", "BLOCKED_ROWS",
                      "EXCLUDED_ROWS", "DEFERRED_ROWS", "CONTRACT_ERROR",
                      "REASON_COUNTS"):
            print("ROUTE_" + _name + ":", _report.get(_name))
        for _issue in (_report.get("ISSUES") or ())[:10]:
            print("ROUTE_ISSUE:", _issue.get("severity"),
                  _issue.get("reason"), _issue.get("field"))
print("RESULT: DIAGNOSED_CACHED_MAPPING_ONLY_NO_TARGET_DML")
