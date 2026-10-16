# %% Source Two CATALOG 30,566-change DEV COMMIT approval guard
# Date 2026-10-16. ONE new Python cell after the owner-run PREVIEW + QA.
# THIS CELL DOES NOT WRITE TARGET TABLES. It arms Cell 6's existing guard.
# Only the existing generic Cell 7 may commit, with explicit owner action.
# Do NOT rerun previous successful CATALOG or SSP COMMIT batches.
import json

route = ("source-two-source", "CATALOG")
dim = {"INSERTS": 0, "UPDATES": 30566, "UNCHANGED": 3113}
fact = {"INSERTS": 0, "UPDATES": 0, "UNCHANGED": 33531}
retirement = {"nodes": 0, "edges": 0, "source_records": 0}
populated = {
    ("sections", "TOPIC_NAME"): 10566,
    ("subsections", "TOPIC_NAME"): 20000,
}
empty = {
    "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_CONTENT_ID",
    "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SOURCE_CONFIRMED_IN_ARCHER",
    "ARCHER_CONTENT_AUTHORITATIVE_SOURCES_SECTION_CONFIRMED_IN_ARCHER",
}
paths = {
    "catalog.groups[].groups[]": 10566,
    "catalog.groups[].groups[].groups[]": 20000,
}


def require(ok, reason):
    if not ok:
        raise RuntimeError("CATALOG_DEV_COMMIT_NOT_ARMED_" + reason)


qa = globals().get("SOURCE_TWO_NEXT_FIVE_QA")
preview = globals().get("PIPELINE_REPORT")
contexts = globals().get("MAPPING_CONTEXTS")
require(isinstance(qa, dict) and isinstance(preview, dict)
        and isinstance(contexts, list), "MISSING_CURRENT_PREVIEW_QA_CONTEXT")
require(
    qa.get("status") == "SOURCE_TWO_75_ROW_CATALOG_FIVE_NEW_FIELDS_READ_ONLY_QA"
    and qa.get("result") == "PASS_VALUES_AND_PATHS_SOURCE_EMPTY_FIELDS_UNTESTED"
    and qa.get("writes_executed") is False
    and qa.get("field_mismatches_total") == 0
    and qa.get("changed_path_gate") == "PASS"
    and qa.get("missing_dim_target_keys") == 0
    and qa.get("source_content_id_vs_root_id_differences") == 0
    and qa.get("mapping_fingerprint_matches_preview") is True
    and qa.get("selected_catalog_mapping_rules") == 62
    and qa.get("updated_path_counts") == paths
    and set(qa.get("fields_with_no_populated_source_data", ())) == empty,
    "CURRENT_READ_ONLY_QA_NOT_ACCEPTED",
)
rows = qa.get("field_results", ())
require(len(rows) == 5, "FIVE_FIELD_QA_REQUIRED")
seen = set()
for item in rows:
    key = (item.get("level"), item.get("field"))
    require(key not in seen, "DUPLICATE_FIELD_RESULT")
    seen.add(key)
    n = populated.get(key, 0)
    require(item.get("source_populated") == n
            and item.get("exact_value_matches") == n
            and item.get("mismatches") == 0
            and item.get("source_empty_target_omitted") ==
                item.get("records_checked") - n,
            "FIELD_COUNTS_CHANGED")

groups = preview.get("groups", ())
require(preview.get("mode") == "PREVIEW"
        and preview.get("status") == "PREVIEW_COMPLETE"
        and preview.get("writes_executed") is False
        and preview.get("commit_attempted") is False
        and len(groups) == 1
        and (groups[0].get("source"), groups[0].get("model")) == route,
        "PREVIEW_ROUTE_CHANGED")
load = groups[0].get("load") or {}
require(load.get("status") == "PREVIEW_PASSED_NO_TARGET_DML"
        and load.get("expected_changes") == {"D": dim, "F": fact}
        and load.get("approved_retirement") == retirement
        and load.get("nodes") == 33679 and load.get("edges") == 33531
        and load.get("source_records") == 148
        and load.get("lineage_gaps") == 0
        and all(load.get(k) is False
                for k in ("writes_executed", "committed", "persisted",
                          "target_dml_attempted")),
        "PREVIEW_ENVELOPE_CHANGED")

require(len(contexts) == 1, "MORE_THAN_ONE_MODEL_ROUTE")
ctx = contexts[0]
cfg = ctx.get("config") or {}
fingerprint = (ctx.get("compiled_plan") or {}).get("mapping_fingerprint")
require((ctx.get("source_key"), cfg.get("OSCAL_MODEL")) == route
        and ctx.get("routing_report", {}).get("STATUS") == "READY"
        and len(ctx.get("mapping_rows") or []) == 62
        and cfg.get("EXECUTE_WRITES") is False
        and (cfg.get("STORAGE_CONTRACT") or {}).get("VERIFIED") is True
        and (cfg.get("STORAGE_CONTRACT") or {}).get("MODEL_KEY") == "CATALOG"
        and isinstance(fingerprint, str) and bool(fingerprint)
        and fingerprint == groups[0].get("mapping_fingerprint"),
        "MAPPING_OR_STORAGE_CONTRACT_CHANGED")

# Optional exact-count guard in existing production Cell 6. The loader
# will check these counts before BEGIN and again inside the transaction.
cfg["APPROVED_COMMIT_CHANGE_ENVELOPE"] = {"D": dict(dim), "F": dict(fact)}
cfg["APPROVED_COMMIT_RETIREMENT_COUNTS"] = dict(retirement)

print(json.dumps({
    "status": "CATALOG_DEV_COMMIT_GUARD_ARMED_NO_WRITES",
    "source": route[0],
    "model": route[1],
    "approved_dim_changes": dim,
    "approved_fact_changes": fact,
    "approved_retirements": retirement,
    "populated_fields_with_exact_value_qa": 2,
    "empty_source_fields_not_value_tested": sorted(empty),
    "mapping_fingerprint_matches_preview": True,
    "writes_executed": False,
    "next_action": "Set existing Cell 7 OSCAL_LOAD_MODE to COMMIT and run Cell 7 ONCE ONLY",
}, indent=2))
