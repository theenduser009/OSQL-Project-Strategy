# %% Cell 7 - Run the mapping
OSCAL_LOAD_MODE = "PREVIEW"  # COMMIT preflights the exact approved route set in this invocation.

if getattr(globals().get("run_oscal_pipeline"), "_oscal_pipeline_release", None) != "oscal-seven-cell-metadata-authority-v1":
    raise ValueError("Run the matching Cell 6 before Cell 7")
_routes = {(context["source_key"], context["config"]["OSCAL_MODEL"]) for context in MAPPING_CONTEXTS}
_scopes = [scope for scope in _daily_write_scopes()
           if scope["policy"]["enabled"] is True and _routes == set(scope["routes"])]
OSCAL_DAILY_WRITE_POLICY = {"policy_id": _scopes[0]["policy"]["policy_id"]} if _scopes else None
MODEL_GRAPHS = PIPELINE_REPORT = None
try:
    MODEL_GRAPHS, PIPELINE_REPORT = run_oscal_pipeline(
        SOURCE_INPUTS, MAPPING_CONTEXTS, OSCAL_LOAD_MODE, daily_write_policy=OSCAL_DAILY_WRITE_POLICY)
except PipelineError as error:
    PIPELINE_REPORT = error.report
    raise
finally:
    print("OSCAL_PIPELINE_REPORT")
    print(json.dumps(PIPELINE_REPORT, indent=2, default=str))
