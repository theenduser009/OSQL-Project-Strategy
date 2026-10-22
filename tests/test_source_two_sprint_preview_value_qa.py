"""Self-contained synthetic tests for the public frozen-preview QA.

No private mapper, CSV, registry, source values, connector or warehouse is used.
Stub frames expose only iteration of already supplied rows; SQL/table/write
access is deliberately unavailable.
"""
import copy
import importlib.util
import json
import runpy
from collections import Counter
from decimal import Decimal
from pathlib import Path
import unittest
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sprint_preview_qa", ROOT / "qa/source_two_sprint_preview_value_qa.py")
QA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QA)

RESULT = "assessment-results.results[]"
AGG = RESULT + ".props[]"
FINDING = RESULT + ".findings[]"
FPROPS = FINDING + ".props[]"
GUID = "1828bb8a-b8f5-4148-807e-b73d7385ca0d"
NAMESPACE = UUID(GUID).urn
CONTROL_PATHS = (
    "catalog.controls[]", "catalog.groups[].controls[]",
    "catalog.groups[].groups[].controls[]",
    "catalog.groups[].groups[].groups[].controls[]")
COMMON = {
    "COMPLIANCE_RATING": ("archer-select", "compliance-rating", AGG),
    "COUNT_OF_NONCOMPLIANT_CONTROLS": ("direct", "noncompliant-count", AGG),
    "PCT_OF_NONCOMPLIANT_CONTROLS": ("direct", "noncompliant-percentage", AGG),
    "FINDINGS": ("reference-ids", "source-finding-reference", FPROPS),
    "CONTROL_TESTING_RESULTS_FAILED_EXTERNAL_CONTROL_REQUIREMENT":
        ("direct", "test-result", FPROPS),
    "DEVIATIONS_AUTHORITATIVE_SOURCES": ("direct", "deviation", FPROPS),
    "EVIDENCE_REPOSITORY": ("direct", "evidence-repository", FPROPS),
}
SUB_ONLY = {
    "DEVIATIONS_AUTHORITATIVE_SOURCES_LINKED_TO_CONTROL_STANDARDS":
        ("reference-ids", "linked-control-standard", FPROPS),
    "DCMA_SCORE_VALUE": ("direct", "dcma-score-value", AGG),
    "DCMA_SCORE_COMMENT": ("direct", "dcma-score-comment", AGG),
}


class Frame:
    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)

    def to_local_iterator(self):
        return iter(self.rows)

    def __getattr__(self, name):
        raise AssertionError("QA attempted an operation outside frozen-row iteration")


def freeze(value):
    if isinstance(value, Frame):
        return freeze(value.rows)
    if isinstance(value, dict):
        return {key: freeze(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    return copy.deepcopy(value)


def fixture():
    graphs, inputs, groups = {}, {}, []
    counts = {"source-two-topic": 7, "source-two-section": 7,
              "source-two-subsection": 10}
    for source, count in counts.items():
        table = "SYNTHETIC_" + source.replace("-", "_").upper()
        fields = dict(COMMON, **(SUB_ONLY if source == "source-two-subsection" else {}))
        nodes, edges, records = [], [], []

        def node(record_id, path, payload, token, parent=None):
            key = source + "/" + record_id + "/" + token
            row = {
                "NODE_KEY": key, "ELEMENT_PATH": path,
                "SOURCE_RECORD_ID": record_id, "SOURCE_TABLE_NAME": table,
                "INSTANCE_KEY": record_id if path != "assessment-results" else "singleton",
                "METADATA_JSON": json.dumps(payload),
            }
            nodes.append(row)
            if parent is not None:
                edges.append({"DEPENDENCY_TYPE": "CONTAINS",
                              "FK_SOURCE_ELEMENT_HASH": parent["NODE_KEY"],
                              "FK_TARGET_ELEMENT_HASH": key})
            return row

        for record_id, count_value in (("101", 0), ("102", 1)):
            raw = {
                "COMPLIANCE_RATING": {
                    "ValuesListIds": [1],
                    "ResolvedValues": [{"ValueId": "1", "ValueName": "N/A",
                                        "LookupStatus": "MATCHED"}]},
                "COUNT_OF_NONCOMPLIANT_CONTROLS": count_value,
            }
            expected = [(AGG, "compliance-rating", "N/A"),
                        (AGG, "noncompliant-count", str(count_value))]
            if record_id == "101":
                raw.update({
                    "PCT_OF_NONCOMPLIANT_CONTROLS": None,
                    "FINDINGS": [11, {"ContentId": 12, "LevelId": 999}, 11],
                    "CONTROL_TESTING_RESULTS_FAILED_EXTERNAL_CONTROL_REQUIREMENT": 0,
                    "DEVIATIONS_AUTHORITATIVE_SOURCES": "synthetic deviation",
                    "EVIDENCE_REPOSITORY": "synthetic opaque evidence",
                })
                expected += [(FPROPS, "source-finding-reference", "11"),
                             (FPROPS, "source-finding-reference", "12"),
                             (FPROPS, "test-result", "0"),
                             (FPROPS, "deviation", "synthetic deviation"),
                             (FPROPS, "evidence-repository", "synthetic opaque evidence")]
                if source == "source-two-subsection":
                    raw.update({
                        "DEVIATIONS_AUTHORITATIVE_SOURCES_LINKED_TO_CONTROL_STANDARDS":
                            [701, 701],
                        "DCMA_SCORE_VALUE": Decimal("0.00"),
                        "DCMA_SCORE_COMMENT": "synthetic  comment\nsecond line",
                    })
                    expected += [(FPROPS, "linked-control-standard", "701"),
                                 (AGG, "dcma-score-value", "0.00"),
                                 (AGG, "dcma-score-comment",
                                  "synthetic  comment\nsecond line")]
            records.append({"SOURCE_RECORD_ID": record_id, "CURATED_JSON": raw})
            root = node(record_id, "assessment-results", {}, "root")
            result = node(record_id, RESULT, {}, "result", root)
            finding = node(record_id, FINDING, {}, "finding", result) if (
                any(path == FPROPS for path, _, _ in expected)) else None
            for index, (path, name, value) in enumerate(expected):
                node(record_id, path, {"name": name, "value": value},
                     "property-" + str(index), finding if path == FPROPS else result)
        fingerprint = "synthetic-" + source
        ctx = {
            "routing_report": {"STATUS": "READY", "SELECTED_ROWS": count},
            "mapping_rows": [{
                "SOURCE_FIELD_NAME": field, "TRANSFORM_ID": transform,
                "OWNER_ELEMENT_PATH": path,
                "REPRESENTATION_PARAMS": {"property_name": name},
            } for field, (transform, name, path) in fields.items()],
            "config": {"EXECUTE_WRITES": False, "SOURCE_TABLE_NAME": table},
            "compiled_plan": {"mapping_fingerprint": fingerprint},
        }
        route = (source, "ASSESSMENT_RESULTS")
        graphs[route] = {"nodes": Frame(nodes), "edges": Frame(edges), "context": ctx}
        inputs[source] = {"source_df": Frame(records),
                          "selection": {"SELECTED_ROWS": 2}}
        groups.append({
            "source": source, "model": route[1], "mapping_fingerprint": fingerprint,
            "load": {"status": "PREVIEW_PASSED_NO_TARGET_DML",
                     "target_dml_attempted": False, "writes_executed": False,
                     "source_records": 2},
        })

    source, table = "source-two-source", "SYNTHETIC_CATALOG_RAW"
    contract = {
        "enabled": True, "source_field": "RELATED_CONTROL_PROCEDURES",
        "namespace_mode": "archer-field-guid-urn", "property_name": "procedure-reference",
        "level_id": 41, "field_id": 30705,
    }
    lookups = {
        "native_control_guid_metadata": {"control-standards": Frame([{
            "LEVEL_ID": 41, "FIELD_ID": 30705, "FIELD_GUID": GUID,
            "SQL_FIELD_NAME": "RELATED_CONTROL_PROCEDURES"}])},
        "native_control_sources": {"control-standards": Frame([{
            "SOURCE_RECORD_ID": "500", "CURATED_JSON": {
                "CONTROL_STANDARD_NAME": "SYNTHETIC-500",
                "CONTROL_STANDARD_REQUIREMENT": None,
                "RELATED_CONTROL_PROCEDURES": [
                    {"ContentId": 9, "LevelId": 39},
                    {"ContentId": 2, "LevelId": 39},
                    {"ContentId": 9, "LevelId": 39}],
            }}])},
    }
    nodes, edges = [], []
    for record_id in ("100", "200"):
        root_key = source + "/" + record_id + "/root"
        control_key = source + "/" + record_id + "/control"
        nodes += [
            {"NODE_KEY": root_key, "ELEMENT_PATH": "catalog",
             "SOURCE_RECORD_ID": record_id, "SOURCE_TABLE_NAME": table,
             "INSTANCE_KEY": "singleton", "METADATA_JSON": "{}"},
            {"NODE_KEY": control_key, "ELEMENT_PATH": CONTROL_PATHS[0],
             "PARENT_NODE_PATH": "catalog", "PARENT_INSTANCE_KEY": "singleton",
             "SOURCE_RECORD_ID": record_id, "SOURCE_TABLE_NAME": table,
             "INSTANCE_KEY": "500", "METADATA_JSON": json.dumps({
                 "id": "SYNTHETIC-500", "title": "Synthetic control",
                 "props": [{"name": "archer-content-id", "value": "500"},
                           {"name": "procedure-reference", "ns": NAMESPACE, "value": "2"},
                           {"name": "procedure-reference", "ns": NAMESPACE, "value": "9"}],
             })},
        ]
        edges.append({"DEPENDENCY_TYPE": "CONTAINS", "FK_SOURCE_ELEMENT_HASH": root_key,
                      "FK_TARGET_ELEMENT_HASH": control_key})
    fingerprint = "synthetic-catalog"
    native_report = {
        "NATIVE_CATALOG_FIELD_VALUE_CHECK": "CANDIDATE_MATCHES_FROZEN_TARGET_FIELDS",
        "NATIVE_CATALOG_GUID_PROPS_FIELD_VALUE_CHECK":
            "STANDARD_OWNED_DEDUPLICATED_LEVEL39_REFERENCES",
        "NATIVE_CATALOG_MISSING_STATEMENT_DEFINITIONS": 2,
    }
    ctx = {
        "routing_report": {"STATUS": "READY", "SELECTED_ROWS": 91},
        "mapping_rows": [{"SOURCE_FIELD_NAME": "SYNTHETIC_LEGACY_" + str(i)}
                         for i in range(87)] + [
                             {"SOURCE_FIELD_NAME": "RELATED_CONTROL_PROCEDURES"}
                             for _ in CONTROL_PATHS],
        "config": {"EXECUTE_WRITES": False, "SOURCE_TABLE_NAME": table},
        "compiled_plan": {"mapping_fingerprint": fingerprint,
                          "native_catalog": {"lookup": "control-standards",
                                             "paths": CONTROL_PATHS,
                                             "fields": {"parts": "CONTROL_STANDARD_REQUIREMENT",
                                                        "": "CONTROL_STANDARDS"},
                                             "owner_bindings": {"catalog": None},
                                             "guid_props": contract}},
        "lookups": lookups, "graph_report": native_report,
    }
    route = (source, "CATALOG")
    graphs[route] = {"nodes": Frame(nodes), "edges": Frame(edges), "context": ctx}
    inputs[source] = {
        "source_df": Frame([{"SOURCE_RECORD_ID": rid,
                            "CURATED_JSON": {"CONTROL_STANDARDS": [500]}}
                           for rid in ("100", "200")]),
        "lookups": lookups, "selection": {"SELECTED_ROWS": 2},
    }
    groups.append({
        "source": source, "model": "CATALOG", "mapping_fingerprint": fingerprint,
        "native_catalog": native_report,
        "load": {"status": "PREVIEW_PASSED_NO_TARGET_DML",
                 "target_dml_attempted": False, "writes_executed": False,
                 "source_records": 2},
    })
    pipeline = {"mode": "PREVIEW", "status": "PREVIEW_COMPLETE",
                "writes_executed": False, "commit_attempted": False, "groups": groups}
    return graphs, inputs, pipeline


class FrozenPreviewQaTests(unittest.TestCase):
    def run_qa(self, case):
        return QA.run_source_two_sprint_value_qa(*case, detail_limit=0)

    def test_healthy_read_only_zero_decimal_null_missing_and_occurrence_counts(self):
        case = fixture()
        before = freeze(case)
        report = self.run_qa(case)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(0, report["error_count"])
        self.assertEqual([], report["missing_statement_id_details_private"])
        self.assertEqual(before, freeze(case))
        self.assertEqual(24, sum(len(row["fields"])
                                 for row in report["child_assessment_results"]))
        for row in report["child_assessment_results"]:
            empty = row["fields"]["PCT_OF_NONCOMPLIANT_CONTROLS"]
            self.assertEqual(0, empty["expected_values"])
            self.assertEqual(0, empty["actual_values"])
            self.assertEqual(2, empty["exact_records"])
            self.assertEqual(2, row["fields"]["COUNT_OF_NONCOMPLIANT_CONTROLS"]["expected_values"])
        statement = report["missing_statement_classification"]
        self.assertEqual(2, statement["missing_statement_occurrences"])
        self.assertEqual(1, statement["distinct_standards_with_missing_statement"])
        self.assertEqual(2, statement["SOURCE_NULL"])

    def test_equal_global_value_counts_cannot_hide_swapped_original_records(self):
        case = fixture()
        nodes = case[0][("source-two-topic", "ASSESSMENT_RESULTS")]["nodes"].rows
        targets = [node for node in nodes if json.loads(
            node["METADATA_JSON"]).get("name") == "noncompliant-count"]
        self.assertEqual(2, len(targets))
        for node in targets:
            value = json.loads(node["METADATA_JSON"])
            value["value"] = "1" if value["value"] == "0" else "0"
            node["METADATA_JSON"] = json.dumps(value)
        report = self.run_qa(case)
        self.assertEqual("REVIEW_REQUIRED", report["result"])
        topic = next(row for row in report["child_assessment_results"]
                     if row["route"] == "source-two-topic")
        metric = topic["fields"]["COUNT_OF_NONCOMPLIANT_CONTROLS"]
        self.assertEqual(2, metric["missing_values"])
        self.assertEqual(2, metric["unexpected_values"])

    def test_property_at_wrong_native_owner_path_requires_review(self):
        case = fixture()
        nodes = case[0][("source-two-topic", "ASSESSMENT_RESULTS")]["nodes"].rows
        target = next(node for node in nodes if json.loads(
            node["METADATA_JSON"]).get("name") == "noncompliant-count")
        target["ELEMENT_PATH"] = FPROPS
        report = self.run_qa(case)
        self.assertGreater(report["error_count"], 0)
        self.assertEqual("REVIEW_REQUIRED", report["result"])

    def test_duplicate_or_wrong_namespace_procedure_props_require_review(self):
        for mode in ("duplicate", "namespace"):
            with self.subTest(mode=mode):
                case = fixture()
                nodes = case[0][("source-two-source", "CATALOG")]["nodes"].rows
                control = next(node for node in nodes if node["ELEMENT_PATH"] == CONTROL_PATHS[0])
                payload = json.loads(control["METADATA_JSON"])
                if mode == "duplicate":
                    payload["props"].append(copy.deepcopy(payload["props"][-1]))
                else:
                    payload["props"][-1]["ns"] = UUID(
                        "2828bb8a-b8f5-4148-807e-b73d7385ca0d").urn
                control["METADATA_JSON"] = json.dumps(payload)
                report = self.run_qa(case)
                self.assertGreater(report["error_count"], 0)
                self.assertEqual("REVIEW_REQUIRED", report["result"])

    def test_duplicate_physical_node_keys_fail_closed_in_both_model_frames(self):
        for route in (("source-two-topic", "ASSESSMENT_RESULTS"),
                      ("source-two-source", "CATALOG")):
            with self.subTest(route=route):
                case = fixture()
                frame = case[0][route]["nodes"]
                frame.rows.append(copy.deepcopy(frame.rows[-1]))
                with self.assertRaisesRegex(RuntimeError, "QA_DUPLICATE_PREVIEW_NODE_KEY"):
                    self.run_qa(case)

    def test_unresolved_select_identity_is_not_counted_as_a_match(self):
        case = fixture()
        raw = case[1]["source-two-topic"]["source_df"].rows[0]["CURATED_JSON"]
        raw["COMPLIANCE_RATING"]["ResolvedValues"][0]["ValueId"] = "different"
        report = self.run_qa(case)
        self.assertEqual("REVIEW_REQUIRED", report["result"])
        topic = next(row for row in report["child_assessment_results"]
                     if row["route"] == "source-two-topic")
        self.assertEqual(1, topic["fields"]["COMPLIANCE_RATING"]["normalization_review"])

    def test_wrong_procedure_level_fails_closed(self):
        case = fixture()
        standard = case[0][("source-two-source", "CATALOG")]["context"]["lookups"][
            "native_control_sources"]["control-standards"].rows[0]["CURATED_JSON"]
        standard["RELATED_CONTROL_PROCEDURES"][0]["LevelId"] = 41
        with self.assertRaisesRegex(RuntimeError, "QA_PROCEDURE_REFERENCE_SHAPE"):
            self.run_qa(case)

    def test_standard_from_wrong_catalog_source_cannot_pass_global_counts(self):
        case = fixture()
        catalog_rows = case[1]["source-two-source"]["source_df"].rows
        catalog_rows[0]["CURATED_JSON"]["CONTROL_STANDARDS"] = []
        report = self.run_qa(case)
        self.assertEqual("REVIEW_REQUIRED", report["result"])
        association = report["catalog_standard_associations"]
        self.assertEqual(1, association["expected_catalog_standard_pairs"])
        self.assertEqual(2, association["actual_control_occurrences"])
        self.assertEqual(1, association["unexpected_associations"])

    def test_same_name_property_from_another_namespace_is_preserved(self):
        case = fixture()
        nodes = case[0][("source-two-source", "CATALOG")]["nodes"].rows
        control = next(node for node in nodes if node["ELEMENT_PATH"] == CONTROL_PATHS[0])
        payload = json.loads(control["METADATA_JSON"])
        payload["props"].append({
            "name": "procedure-reference",
            "ns": UUID("2828bb8a-b8f5-4148-807e-b73d7385ca0d").urn,
            "value": "synthetic other field"})
        control["METADATA_JSON"] = json.dumps(payload)
        before = freeze(case)
        report = self.run_qa(case)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(before, freeze(case))
        self.assertEqual(1, report["procedure_by_control_path"][CONTROL_PATHS[0]][
            "preserved_same_name_other_namespace"])

    def test_scalar_select_id_and_normalized_reference_wrapper_match(self):
        case = fixture()
        raw = case[1]["source-two-topic"]["source_df"].rows[0]["CURATED_JSON"]
        raw["COMPLIANCE_RATING"]["ValuesListIds"] = 1
        raw["FINDINGS"] = {"ValueListIDs": [11, 12, 11]}
        report = self.run_qa(case)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(0, report["error_count"])

    def test_populated_statement_source_missing_from_two_catalog_definitions_is_two_errors(self):
        case = fixture()
        standard = case[0][("source-two-source", "CATALOG")]["context"]["lookups"][
            "native_control_sources"]["control-standards"].rows[0]["CURATED_JSON"]
        standard["CONTROL_STANDARD_REQUIREMENT"] = "synthetic populated statement"
        report = self.run_qa(case)
        self.assertEqual("REVIEW_REQUIRED", report["result"])
        self.assertEqual(2, report["missing_statement_classification"][
            "populated_source_missing_statement"])


    def test_script_requires_complete_retained_preview_session(self):
        script = str(ROOT / "qa/source_two_sprint_preview_value_qa.py")
        for initial in ({}, {"MODEL_GRAPHS": {}}):
            with self.subTest(initial_globals=list(initial)):
                with self.assertRaisesRegex(RuntimeError, "QA_PREVIEW_SESSION_REQUIRED"):
                    runpy.run_path(script, init_globals=initial, run_name="__main__")


if __name__ == "__main__":
    unittest.main()
