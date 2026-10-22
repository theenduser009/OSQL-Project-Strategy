"""AUTHORIZED EXACT DEV COMMIT — standalone Cell 9, same active frozen session.

Owner approved the proposal at private commit08bd1f: 6,294 Catalog DIM updates,
128,063 child AR DIM inserts, 96,081 child FACT inserts, zero retirements.
Run this file ONCE in a new Python Cell9 AFTER the accepted Cell8 in the SAME
session. Leave Cells1-8, source snapshots, runtime code, CSVs and registry alone.
This calls only the EXISTING Cell7 pipeline and its mandatory approval guards.

Four independent route transactions can partially commit. On any failure,
retain SOURCE_TWO_SPRINT_COMMIT_REPORT, stop and inspect completed routes;
do not blindly rerun this file or all four routes. Successful completion must
report COMMITTED_AND_VERIFIED; full OSCAL document conformance is not claimed.
The original MODEL_GRAPHS/PIPELINE_REPORT preview globals remain unchanged.
"""
OWNER_APPROVED_DEV_COMMIT = True
import copy
import json

SOURCE_TWO_SPRINT_ROUTES = (
    ("source-two-source", "CATALOG"),
    ("source-two-topic", "ASSESSMENT_RESULTS"),
    ("source-two-section", "ASSESSMENT_RESULTS"),
    ("source-two-subsection", "ASSESSMENT_RESULTS"),
)
SOURCE_TWO_SPRINT_APPROVAL = {
    ("source-two-source", "CATALOG"): {
        "fingerprint": "15ab451deb674db10b2e7c183490675575231d24b25742c3ea2dc2d4a14cf27e",
        "selected_rules": 91, "source_records": 148,
        "source_table": "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_RAW",
        "changes": {
            "D": {"INSERTS": 0, "UPDATES": 6294, "UNCHANGED": 38375},
            "F": {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 44521}}},
    ("source-two-topic", "ASSESSMENT_RESULTS"): {
        "fingerprint": "81b779d3d32f69d06624e542d0ab3eea6e4f7d4e8c773e983fae7a7dfb66157f",
        "selected_rules": 7, "source_records": 1416,
        "source_table": "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_TOPIC_RAW",
        "changes": {
            "D": {"INSERTS": 5664, "UPDATES": 0, "UNCHANGED": 0},
            "F": {"INSERTS": 4248, "UPDATES": 0, "UNCHANGED": 0}}},
    ("source-two-section", "ASSESSMENT_RESULTS"): {
        "fingerprint": "2a8f8a330e7003e0d620ee4c59d95bcd2bf394775843d318bb3104750f880a25",
        "selected_rules": 7, "source_records": 10566,
        "source_table": "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_RAW",
        "changes": {
            "D": {"INSERTS": 42266, "UPDATES": 0, "UNCHANGED": 0},
            "F": {"INSERTS": 31700, "UPDATES": 0, "UNCHANGED": 0}}},
    ("source-two-subsection", "ASSESSMENT_RESULTS"): {
        "fingerprint": "4922b45843fb21b937484226efebdb1555314a51e68cc87a8c05b8b416047c53",
        "selected_rules": 10, "source_records": 20000,
        "source_table": "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SUB_SECTION_RAW",
        "changes": {
            "D": {"INSERTS": 80133, "UPDATES": 0, "UNCHANGED": 0},
            "F": {"INSERTS": 60133, "UPDATES": 0, "UNCHANGED": 0}}},
}
SOURCE_TWO_SPRINT_RETIREMENT = {"nodes": 0, "edges": 0, "source_records": 0}
SOURCE_TWO_SPRINT_TARGET_PREFIX = "RTX_ENTERPRISESERVICES_DEV.ES_ESC_GRC_CURATED."

def _sprint_require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def _sprint_copy_containers(value):
    # Preserve each existing cached Snowpark frame handle; copy only containers.
    if isinstance(value, dict):
        return {key: _sprint_copy_containers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sprint_copy_containers(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sprint_copy_containers(item) for item in value)
    return value

def _sprint_frame_ids(value, path=""):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(_sprint_frame_ids(item, path + "/" + str(key)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(_sprint_frame_ids(item, path + "/" + str(index)))
    elif hasattr(value, "to_local_iterator"):
        found.append((path, id(value)))
    return tuple(sorted(found))

def _sprint_qa_core(report):
    return {key: value for key, value in report.items()
            if key != "missing_statement_id_details_private"}

def _sprint_validate_qa(report):
    _sprint_require(isinstance(report, dict) and report.get("result") == "PASS"
                    and type(report.get("error_count")) is int
                    and report["error_count"] == 0, "SPRINT_CURRENT_QA_PASS_REQUIRED")
    associations = report.get("catalog_standard_associations", {})
    _sprint_require(associations.get("expected_catalog_standard_pairs") == 10422
                    and associations.get("actual_control_occurrences") == 10422
                    and associations.get("missing_associations") == 0
                    and associations.get("unexpected_associations") == 0,
                    "SPRINT_QA_ASSOCIATION_SCOPE_CHANGED")
    metrics = list(report.get("procedure_by_control_path", {}).values())
    _sprint_require(sum(row.get("expected_values", 0) for row in metrics) == 410598
                    and sum(row.get("actual_values", 0) for row in metrics) == 410598
                    and sum(row.get("exact_control_occurrences", 0) for row in metrics) == 10422,
                    "SPRINT_QA_PROCEDURE_SCOPE_CHANGED")
    missing = report.get("missing_statement_classification", {})
    _sprint_require(missing.get("missing_statement_occurrences") == 5
                    and missing.get("SOURCE_NULL") == 5
                    and missing.get("distinct_standards_with_missing_statement") == 3
                    and missing.get("populated_source_missing_statement", 0) == 0,
                    "SPRINT_STATEMENT_CLASSIFICATION_CHANGED")

def prepare_source_two_sprint_commit_inputs(
        model_graphs, source_inputs, pipeline_report, mapping_contexts,
        current_qa, qa_function, *, arm=False):
    """Return reviewed pinned inputs; NEVER execute a pipeline or write.

    arm=False validates existing in-memory evidence and returns REVIEW_ONLY.
    arm=True additionally repeats the independent QA over existing cached frames,
    then returns separate contexts with the fixed approval envelope. It does not
    change MODEL_GRAPHS, SOURCE_INPUTS, MAPPING_CONTEXTS, PIPELINE_REPORT or mode.
    No RAW/target query is made by this helper. The provided QA function may SELECT
    the already cached Cell 2 snapshots, exactly as the completed owner QA did.
    """
    _sprint_require(type(arm) is bool, "SPRINT_ARM_MUST_BE_BOOLEAN")
    _sprint_validate_qa(current_qa)
    expected_routes = set(SOURCE_TWO_SPRINT_ROUTES)
    _sprint_require(set(model_graphs) == expected_routes
                    and set(source_inputs) == {route[0] for route in expected_routes},
                    "SPRINT_EXPECTED_FOUR_ROUTES")
    contexts = {(ctx["source_key"], ctx["config"]["OSCAL_MODEL"]): ctx
                for ctx in mapping_contexts}
    groups = {(group.get("source"), group.get("model")): group
              for group in pipeline_report.get("groups", [])}
    _sprint_require(len(mapping_contexts) == len(contexts) == 4
                    and set(contexts) == expected_routes and set(groups) == expected_routes
                    and len(pipeline_report["groups"]) == 4,
                    "SPRINT_DUPLICATE_OR_MISSING_ROUTE")
    _sprint_require(pipeline_report.get("mode") == "PREVIEW"
                    and pipeline_report.get("status") == "PREVIEW_COMPLETE"
                    and pipeline_report.get("writes_executed") is False
                    and pipeline_report.get("commit_attempted") is False,
                    "SPRINT_SUCCESSFUL_PREVIEW_REQUIRED")
    for route in SOURCE_TWO_SPRINT_ROUTES:
        approved = SOURCE_TWO_SPRINT_APPROVAL[route]
        ctx, graph_ctx, group = contexts[route], model_graphs[route]["context"], groups[route]
        load = group["load"]
        for candidate in (ctx, graph_ctx):
            config = candidate["config"]
            storage = config.get("STORAGE_CONTRACT") or {}
            _sprint_require(candidate["compiled_plan"].get("mapping_fingerprint") == approved["fingerprint"]
                            and candidate["routing_report"].get("STATUS") == "READY"
                            and candidate["routing_report"].get("SELECTED_ROWS") == approved["selected_rules"]
                            and len(candidate["mapping_rows"]) == approved["selected_rules"],
                            "SPRINT_MAPPING_FINGERPRINT_OR_SELECTION_CHANGED")
            _sprint_require(config.get("EXECUTE_WRITES") is False
                            and config.get("SOURCE_SYSTEM_NAME") == "ARCHER"
                            and config.get("SOURCE_TABLE_NAME") == approved["source_table"]
                            and storage.get("VERIFIED") is True
                            and storage.get("SOURCE_TABLE_NAME") == approved["source_table"]
                            and storage.get("TARGET_DIM") == SOURCE_TWO_SPRINT_TARGET_PREFIX + "DIM_OSCAL_" + route[1] + "_ELEMENT"
                            and storage.get("TARGET_FACT") == SOURCE_TWO_SPRINT_TARGET_PREFIX + "FACT_OSCAL_" + route[1] + "_DEPENDENCY",
                            "SPRINT_VERIFIED_DEV_DESTINATION_CHANGED")
        _sprint_require(ctx["config"].get("RUN_ID") == graph_ctx["config"].get("RUN_ID")
                        and graph_ctx.get("lookups") is source_inputs[route[0]].get("lookups"),
                        "SPRINT_FROZEN_SESSION_HANDLES_CHANGED")
        _sprint_require(group.get("mapping_fingerprint") == approved["fingerprint"]
                        and source_inputs[route[0]]["selection"].get("SELECTED_ROWS") == approved["source_records"]
                        and load.get("source_records") == approved["source_records"]
                        and load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
                        and load.get("target_dml_attempted") is False
                        and load.get("writes_executed") is False
                        and load.get("validation_passed") is True
                        and load.get("storage_verified") is True
                        and load.get("lineage_gaps") == 0
                        and load.get("approved_retirement") == SOURCE_TWO_SPRINT_RETIREMENT,
                        "SPRINT_PREVIEW_EVIDENCE_CHANGED")
        observed = load.get("expected_changes")
        _sprint_require(isinstance(observed, dict) and set(observed) == {"D", "F"}
                        and all(isinstance(observed[kind], dict)
                                and set(observed[kind]) == {"INSERTS", "UPDATES", "UNCHANGED"}
                                and all(type(value) is int for value in observed[kind].values())
                                for kind in ("D", "F"))
                        and observed == approved["changes"],
                        "SPRINT_FIXED_APPROVED_DELTA_CHANGED")
    summary = {"state": "REVIEW_ONLY", "armed": False,
               "mode": "PREVIEW", "routes": [
                   {"source": route[0], "model": route[1],
                    "mapping_fingerprint": SOURCE_TWO_SPRINT_APPROVAL[route]["fingerprint"],
                    "approved_changes": copy.deepcopy(SOURCE_TWO_SPRINT_APPROVAL[route]["changes"]),
                    "approved_retirement": dict(SOURCE_TWO_SPRINT_RETIREMENT)}
                   for route in SOURCE_TWO_SPRINT_ROUTES],
               "execution": "NONE; no loader/pipeline call or global-context mutation",
               "transaction_boundary": "Four independent route transactions; partial commit is possible"}
    if not arm:
        return {"summary": summary}
    _sprint_require(callable(qa_function), "SPRINT_CURRENT_QA_FUNCTION_REQUIRED")
    handles_before = (_sprint_frame_ids(source_inputs), _sprint_frame_ids(model_graphs))
    fresh_qa = qa_function(model_graphs, source_inputs, pipeline_report, detail_limit=0)
    _sprint_validate_qa(fresh_qa)
    _sprint_require(_sprint_qa_core(fresh_qa) == _sprint_qa_core(current_qa)
                    and handles_before == (_sprint_frame_ids(source_inputs), _sprint_frame_ids(model_graphs)),
                    "SPRINT_QA_OR_SNAPSHOT_HANDLES_CHANGED")
    pinned_inputs = _sprint_copy_containers(source_inputs)
    armed_contexts = []
    for route in SOURCE_TWO_SPRINT_ROUTES:
        cloned = copy.deepcopy(contexts[route])
        cloned["config"]["APPROVED_COMMIT_CHANGE_ENVELOPE"] = copy.deepcopy(
            SOURCE_TWO_SPRINT_APPROVAL[route]["changes"])
        cloned["config"]["APPROVED_COMMIT_RETIREMENT_COUNTS"] = dict(SOURCE_TWO_SPRINT_RETIREMENT)
        # Shared write default stays False; only existing Cell 7 chooses COMMIT.
        _sprint_require(cloned["config"].get("EXECUTE_WRITES") is False, "SPRINT_SHARED_WRITE_FLAG_CHANGED")
        armed_contexts.append(cloned)
    summary.update(state="APPROVED_CONTEXTS_PREPARED_NO_EXECUTION", armed=True)
    return {"summary": summary, "source_inputs": pinned_inputs,
            "mapping_contexts": armed_contexts, "load_mode": "PREVIEW",
            "snapshot_frame_ids": handles_before[0]}


def execute_owner_approved_source_two_sprint_commit(namespace, *, owner_approved=False):
    """Execute only the explicitly authorized exact DEV scope via Cell7.

    Tests may supply stubbed existing notebook functions. The owner entry point
    below supplies the actual current notebook globals; no alternate engine or
    loader implementation is supplied by this file.
    """
    previous = namespace.get("SOURCE_TWO_SPRINT_COMMIT_REPORT")
    if isinstance(previous, dict) and (
            previous.get("commit_attempted") in (True, "UNKNOWN")
            or previous.get("writes_executed") in (True, "UNKNOWN")
            or previous.get("status") == "COMMITTED_AND_VERIFIED"):
        print("SOURCE_TWO_SPRINT_COMMIT_REPORT")
        print(json.dumps(previous, indent=2, default=str))
        raise RuntimeError("SPRINT_PRIOR_COMMIT_ATTEMPT_STOP_AND_REVIEW")
    graphs = None
    report = {"mode": "COMMIT", "status": "PREPARATION_BLOCKED", "groups": [],
              "writes_executed": False, "commit_attempted": False}
    phase = "PREPARATION"
    namespace["SOURCE_TWO_SPRINT_COMMIT_PREPARATION"] = None
    try:
        _sprint_require(owner_approved is True, "SPRINT_EXACT_OWNER_APPROVAL_REQUIRED")
        required = ("MODEL_GRAPHS", "SOURCE_INPUTS", "PIPELINE_REPORT", "MAPPING_CONTEXTS",
                    "SOURCE_TWO_SPRINT_VALUE_QA", "run_source_two_sprint_value_qa",
                    "run_oscal_pipeline", "validate_and_load_oscal", "build_oscal_graph")
        _sprint_require(all(name in namespace for name in required),
                        "SPRINT_SAME_ACTIVE_PREVIEW_AND_QA_SESSION_REQUIRED")
        _sprint_require(callable(namespace["run_oscal_pipeline"])
                        and getattr(namespace["validate_and_load_oscal"], "_oscal_loader_release", None)
                            == "oscal-lean-daily-v3.4.1-required-approval"
                        and getattr(namespace["build_oscal_graph"], "_oscal_mapper_release", None)
                            == "lean-csv-registry-v18-native-catalog-bulk",
                        "SPRINT_MATCHING_REQUIRED_APPROVAL_RUNTIME_REQUIRED")
        prepared = prepare_source_two_sprint_commit_inputs(
            namespace["MODEL_GRAPHS"], namespace["SOURCE_INPUTS"],
            namespace["PIPELINE_REPORT"], namespace["MAPPING_CONTEXTS"],
            namespace["SOURCE_TWO_SPRINT_VALUE_QA"],
            namespace["run_source_two_sprint_value_qa"], arm=True)
        _sprint_require(prepared["summary"].get("armed") is True,
                        "SPRINT_APPROVED_CONTEXT_PREPARATION_REQUIRED")
        namespace["SOURCE_TWO_SPRINT_COMMIT_PREPARATION"] = prepared["summary"]
        phase = "EXISTING_CELL7_PIPELINE"
        graphs, report = namespace["run_oscal_pipeline"](
            prepared["source_inputs"], prepared["mapping_contexts"], load_mode="COMMIT")
        _sprint_require(report.get("mode") == "COMMIT"
                        and report.get("status") == "COMMITTED_AND_VERIFIED",
                        "SPRINT_COMMIT_SUCCESS_NOT_CONFIRMED")
        return graphs, report
    except BaseException as error:
        pipeline_report = getattr(error, "report", None)
        if phase == "EXISTING_CELL7_PIPELINE" and isinstance(pipeline_report, dict):
            report = pipeline_report
        elif phase == "PREPARATION":
            report.update(status="PREPARATION_BLOCKED", error_type=type(error).__name__,
                          reason=str(error) if type(error) is RuntimeError
                          and str(error).startswith("SPRINT_") else "Inspect protected notebook error")
        else:
            # An unexpected runner failure cannot prove that no write occurred.
            # Preserve a returned report if available; otherwise mark unknown.
            if not isinstance(report, dict) or report.get("status") == "PREPARATION_BLOCKED":
                report = {"mode": "COMMIT", "status": "COMMIT_CALL_FAILED_REVIEW_REQUIRED",
                          "groups": [], "writes_executed": "UNKNOWN",
                          "commit_attempted": "UNKNOWN", "error_type": type(error).__name__}
            else:
                report = dict(report, review_required=True, error_type=type(error).__name__)
        raise
    finally:
        namespace["SOURCE_TWO_SPRINT_COMMIT_GRAPHS"] = graphs
        namespace["SOURCE_TWO_SPRINT_COMMIT_REPORT"] = report
        print("SOURCE_TWO_SPRINT_COMMIT_REPORT")
        print(json.dumps(report, indent=2, default=str))

# Single owner-authorized entry point. Module import without notebook globals
# remains inert for cloud tests; normal script/cell execution requires them.
_sprint_runtime_names = ("MODEL_GRAPHS", "SOURCE_INPUTS", "PIPELINE_REPORT", "MAPPING_CONTEXTS")
if __name__ == "__main__" or any(name in globals() for name in _sprint_runtime_names):
    execute_owner_approved_source_two_sprint_commit(
        globals(), owner_approved=OWNER_APPROVED_DEV_COMMIT)
