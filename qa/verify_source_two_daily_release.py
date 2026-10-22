"""Verify the pinned, external-file daily release without Snowflake or DML.

This is a deployment/CI verifier, not an additional mapper notebook cell.
It reads package files, compiles Python without executing runtime cells, and
runs the real CSV reader extracted from Cell 2 against each configured file.
"""
import argparse
import ast
import copy
import csv
import hashlib
import json
from pathlib import Path

SOURCE_REVISION = "2ad83d8f0862f0cb7dd5868b46130c8042d837d4"
EXPECTED_FILES = {
    "01_initialization_and_configuration.py": "daf49c6ea3a3eab1ef42d357046e2061b7da6cda",
    "02_source_mapping_registry_inputs.py": "6cdd8cee23ee2d287fb2a4a2c7c1c84a43a5746a",
    "03_canonical_mapping_contract.py": "34c3e265922a07da5a07586ca930e33cb936d62a",
    "04_parsing_transform_payload_helpers.py": "97f9000b525a6b2ea77acbac416c09536e07b9bc",
    "05_registry_graph_builder.py": "b98e4c977918c4f7a64d5fb5d653d9ca7f9cc15a",
    "06_validation_and_guarded_loader.py": "081cf12014b62a405156fcd6754b701ac403ba4e",
    "07_mapper_orchestrator.py": "4bccff6951ab9604dbb39cb13cd1ae8dbd029a9b",
    "section_assessment_results_runtime.csv": "a278c4c0c2009ea6dad730428180d7cd3dd5b6b0",
    "sources_source_runtime.csv": "a1f1d2d75fe61827c52d041cca194cab3a820365",
    "subsection_assessment_results_runtime.csv": "ae1253122cabdea54af0faac31886348ebb68dd8",
    "topic_assessment_results_runtime.csv": "ea169a2a6fd6c36f32e24d5a8356c1233d9fcdbd"
}
EXPECTED_ROUTES = [
    {
        "source_key": "source-two-source",
        "model": "CATALOG",
        "mapping_file": "sources_source_runtime.csv",
        "selected_rules": 91
    },
    {
        "source_key": "source-two-topic",
        "model": "ASSESSMENT_RESULTS",
        "mapping_file": "topic_assessment_results_runtime.csv",
        "selected_rules": 7
    },
    {
        "source_key": "source-two-section",
        "model": "ASSESSMENT_RESULTS",
        "mapping_file": "section_assessment_results_runtime.csv",
        "selected_rules": 7
    },
    {
        "source_key": "source-two-subsection",
        "model": "ASSESSMENT_RESULTS",
        "mapping_file": "subsection_assessment_results_runtime.csv",
        "selected_rules": 10
    }
]

def _blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _assignment_name(node):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None

def _configuration(source):
    wanted = {"MAPPING_COLUMNS", "MAPPING_OPTIONAL_COLUMNS", "SOURCE_FILES",
              "MODEL_CONTRACTS", "SELECTED_MODELS"}
    nodes = [node for node in ast.parse(source).body if _assignment_name(node) in wanted]
    if {_assignment_name(node) for node in nodes} != wanted or len(nodes) != len(wanted):
        raise ValueError("Daily release configuration assignments are incomplete")
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<verified Cell 1 configuration>", "exec"), namespace)
    return namespace

def _reader(source):
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name == "load_mapping_rows"]
    if len(nodes) != 1:
        raise ValueError("The accepted mapping reader is missing")
    namespace = {"csv": csv}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<verified Cell 2 reader>", "exec"), namespace)
    return namespace["load_mapping_rows"]

def verify_daily_release(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "DAILY_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    expected_manifest_files = {name: {"git_blob_sha1": sha} for name, sha in EXPECTED_FILES.items()}
    if (manifest.get("schema_version") != 1
            or manifest.get("source_revision") != SOURCE_REVISION
            or manifest.get("delivery") != "persistent-external-files"
            or manifest.get("runtime_cells") != 7
            or manifest.get("default_mode") != "PREVIEW"
            or manifest.get("notebook_file") != "SOURCE_TWO_DAILY.ipynb"
            or manifest.get("files") != expected_manifest_files
            or manifest.get("routes") != EXPECTED_ROUTES):
        raise ValueError("Daily release manifest does not match the approved pinned package")
    if list(root.glob("00*.py")):
        raise ValueError("Temporary preparation/bootstrap scripts do not belong in the daily release")
    texts = {}
    for name, expected in EXPECTED_FILES.items():
        raw = (root / name).read_bytes()
        if _blob_sha(raw) != expected:
            raise ValueError("Daily release file integrity mismatch: " + name)
        texts[name] = raw.decode("utf-8")
        if name.endswith(".py"):
            compile(texts[name], name, "exec")
    notebook = json.loads((root / "SOURCE_TWO_DAILY.ipynb").read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    py_names = sorted(name for name in EXPECTED_FILES if name.endswith(".py"))
    if notebook.get("nbformat") != 4 or len(cells) != 7:
        raise ValueError("Git-importable notebook must contain exactly seven cells")
    for cell, name in zip(cells, py_names):
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        if (cell.get("cell_type") != "code" or source != texts[name]
                or cell.get("outputs") != [] or cell.get("execution_count") is not None):
            raise ValueError("Git-importable notebook differs from accepted runtime")
    config = _configuration(texts["01_initialization_and_configuration.py"])
    if tuple(config["SELECTED_MODELS"]) != ("CATALOG", "ASSESSMENT_RESULTS"):
        raise ValueError("Daily source/model selection changed")
    profiles = config["SOURCE_FILES"]
    if [profile.get("SOURCE_KEY") for profile in profiles] != [route["source_key"] for route in EXPECTED_ROUTES]:
        raise ValueError("Daily source selection changed")
    read_rows = _reader(texts["02_source_mapping_registry_inputs.py"])
    counts = []
    for profile, route in zip(profiles, EXPECTED_ROUTES):
        if (profile.get("MAPPING_FILE") != route["mapping_file"]
                or tuple(profile.get("MODEL_BINDINGS", ())) != (route["model"],)
                or profile.get("MAPPING_SOURCE_COLUMN") != "SOURCE_KEY"
                or profile.get("MAPPING_SOURCE_VALUE") != route["source_key"]):
            raise ValueError("Daily route configuration changed")
        deployed = copy.deepcopy(profile)
        deployed["MAPPING_FILE"] = str(root / route["mapping_file"])
        rows = read_rows(deployed)
        aliases = {name.strip().upper() for name in config["MODEL_CONTRACTS"][route["model"]]["MODEL_ALIASES"]}
        selected = [row for row in rows
                    if str(row.get("EXECUTION_STATUS") or "").strip().upper() == "APPROVED"
                    and str(row.get("OSCAL_MODEL") or "").strip().upper() in aliases]
        if len(selected) != route["selected_rules"]:
            raise ValueError("Daily route selected mapping count changed")
        counts.append(len(selected))
    modes = [node.value.value for node in ast.parse(texts["07_mapper_orchestrator.py"]).body
             if _assignment_name(node) == "OSCAL_LOAD_MODE" and isinstance(node.value, ast.Constant)]
    if modes != ["PREVIEW"]:
        raise ValueError("Daily package must preserve the accepted PREVIEW default")
    return {"status": "VERIFIED", "runtime_cells": 7,
            "selected_rule_counts": counts, "fresh_start_mapping_inputs": True,
            "warehouse_contacted": False, "warehouse_installation": "NOT_VERIFIED",
            "daily_commit_policy": "NOT_ACTIVATED"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_daily_release(args.directory), indent=2))

if __name__ == "__main__":
    main()
