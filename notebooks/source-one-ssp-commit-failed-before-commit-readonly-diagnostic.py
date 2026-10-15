# 2026-10-15 — Source One SSP FAILED_BEFORE_COMMIT / AttributeError diagnosis
# Execute ONLY in a NEW PYTHON cell of the currently active Snowflake notebook.
# This rebuilds the graph and runs the shared PREVIEW validator with writes FALSE.
# It CANNOT run the commit branch, MERGE targets, or write DIM/FACT rows.
# The existing notebook's Cells 1–6 and cached SOURCE_INPUTS must still be available.
# Run time may be substantial for a full SSP graph. Do not rerun Cell 7 COMMIT.
#
# Print only the exception class, its last Python stack frames, and stage/status.
# No source records are printed by this script; review logs before sharing.

import copy as _oscal_debug_copy
import traceback as _oscal_debug_traceback

_stage = "select SSP context"
try:
    _contexts = [
        c for c in MAPPING_CONTEXTS
        if c.get("source_key") == "source-one"
        and c.get("config", {}).get("OSCAL_MODEL") == "SSP"
    ]
    if len(_contexts) != 1:
        raise ValueError("Expected exactly one Source One SSP mapping context")

    _stage = "copy compiled context"
    _ctx = _oscal_debug_copy.deepcopy(_contexts[0])
    _source = SOURCE_INPUTS["source-one"]
    _ctx["lookups"] = _source.get("lookups", {})
    _selected = _source.get("selection", {}).get("SELECTED_ROWS")
    if _selected is not None:
        _ctx["config"]["EXPECTED_SOURCE_RECORDS"] = _selected

    _stage = "build source-one SSP candidate graph"
    print("SOURCE_ONE_SSP_COMMIT_FAILURE_DIAGNOSTIC")
    print("Stage:", _stage)
    _nodes, _edges = build_oscal_graph(
        _source["source_df"], None, None,
        _ctx["config"]["OSCAL_MODEL"],
        _ctx["config"]["SOURCE_SYSTEM_NAME"],
        _ctx["config"]["SOURCE_TABLE_NAME"],
        context=_ctx,
    )

    _stage = "validate and compare PREVIEW only (no target DML)"
    print("Stage:", _stage)
    _cfg = dict(_ctx["config"], EXECUTE_WRITES=False)
    _result = validate_and_load_oscal(_nodes, _edges, _cfg)
    print("Result:", _result.get("status"))
    print("Writes executed:", _result.get("writes_executed"))
    print("DIAGNOSTIC_OUTCOME: PREVIEW_REPLAY_PASSED")
except Exception as _error:
    print("FAILED_STAGE:", _stage)
    print("ROOT_EXCEPTION_TYPE:", type(_error).__name__)
    print("ROOT_EXCEPTION_MESSAGE:", str(_error)[:500])
    print("LAST_PYTHON_FRAMES:")
    for _frame in _oscal_debug_traceback.extract_tb(_error.__traceback__)[-8:]:
        print(f"  {_frame.name} @ line {_frame.lineno} ({_frame.filename})")
    print("DIAGNOSTIC_OUTCOME: FAILED_NO_COMMIT_ATTEMPTED_BY_THIS_SCRIPT")
