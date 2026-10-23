"""Read-only artifact verification for the isolated notebook's Source Two CSV.

This deployment/CI utility does not execute runtime cells, generate mappings,
connect to Snowflake, install files or authorize warehouse writes.
"""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

EXPECTED_FILES = {
    "01_initialization_and_configuration.py": "42992094c63927959722abc5fb54c01daba06574",
    "02_source_mapping_registry_inputs.py": "6cdd8cee23ee2d287fb2a4a2c7c1c84a43a5746a",
    "03_canonical_mapping_contract.py": "34c3e265922a07da5a07586ca930e33cb936d62a",
    "04_parsing_transform_payload_helpers.py": "97f9000b525a6b2ea77acbac416c09536e07b9bc",
    "05_registry_graph_builder.py": "b98e4c977918c4f7a64d5fb5d653d9ca7f9cc15a",
    "06_validation_and_guarded_loader.py": "081cf12014b62a405156fcd6754b701ac403ba4e",
    "07_mapper_orchestrator.py": "4bccff6951ab9604dbb39cb13cd1ae8dbd029a9b",
    "sources_source_runtime.csv": "d4f3331af5ab1d31d4e61d2242c6d5db158f5a0d"
}
EXPECTED_ROUTES = [
    {
        "source_key": "source-two-source",
        "model": "CATALOG",
        "input_rows": 110,
        "selected_rows": 93
    },
    {
        "source_key": "source-two-topic",
        "model": "ASSESSMENT_RESULTS",
        "input_rows": 7,
        "selected_rows": 7
    },
    {
        "source_key": "source-two-section",
        "model": "ASSESSMENT_RESULTS",
        "input_rows": 10,
        "selected_rows": 10
    },
    {
        "source_key": "source-two-subsection",
        "model": "ASSESSMENT_RESULTS",
        "input_rows": 16,
        "selected_rows": 16
    }
]
MAPPING_FILE = "sources_source_runtime.csv"

def _blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _name(node):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id

def _config(source):
    wanted = {"MAPPING_COLUMNS","MAPPING_OPTIONAL_COLUMNS","SOURCE_FILES",
              "MODEL_CONTRACTS","SELECTED_MODELS"}
    nodes = [n for n in ast.parse(source).body if _name(n) in wanted]
    if len(nodes) != len(wanted) or {_name(n) for n in nodes} != wanted:
        raise ValueError("Configuration declarations changed")
    namespace = {}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"<verified configuration>","exec"),namespace)
    return namespace

def _reader(source):
    nodes = [n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)
             and n.name == "load_mapping_rows"]
    if len(nodes) != 1:
        raise ValueError("Accepted CSV reader is missing")
    namespace = {"csv":csv}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"<verified CSV reader>","exec"),namespace)
    return namespace["load_mapping_rows"]

def verify_release(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root/"MANIFEST.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != 1 or manifest.get("files") != EXPECTED_FILES
            or manifest.get("delivery") != "isolated-notebook-source-two-approved-extensions"
            or manifest.get("mapping_file") != MAPPING_FILE
            or manifest.get("routes") != EXPECTED_ROUTES
            or manifest.get("input_rows") != 143 or manifest.get("selected_rules") != 126):
        raise ValueError("Single-CSV manifest does not match the pinned candidate")
    if {p.name for p in root.glob("*.csv")} != {MAPPING_FILE} or list(root.glob("00*.py")):
        raise ValueError("Candidate must contain one external Source Two CSV and no preparation script")
    texts = {}
    for name,sha in EXPECTED_FILES.items():
        raw = (root/name).read_bytes()
        if _blob(raw) != sha:
            raise ValueError("Candidate file integrity mismatch: "+name)
        texts[name] = raw.decode("utf-8-sig")
        if name.endswith(".py"):
            compile(texts[name],name,"exec")
    config = _config(texts["01_initialization_and_configuration.py"])
    if tuple(config["SELECTED_MODELS"]) != ("CATALOG","ASSESSMENT_RESULTS"):
        raise ValueError("Selected models changed")
    profiles = config["SOURCE_FILES"]
    if [p.get("SOURCE_KEY") for p in profiles] != [r["source_key"] for r in EXPECTED_ROUTES]:
        raise ValueError("Source route partition changed")
    with (root/MAPPING_FILE).open(encoding="utf-8-sig",newline="") as handle:
        raw_rows = list(csv.DictReader(handle,strict=True))
    keys = Counter(r.get("SOURCE_KEY") for r in raw_rows)
    if dict(keys) != {r["source_key"]:r["input_rows"] for r in EXPECTED_ROUTES}:
        raise ValueError("Unknown, blank or incomplete source partition")
    identities = [(r.get("SOURCE_KEY"),r.get("SOURCE_FIELD_NAME"),r.get("OSCAL_ELEMENT_PATH")) for r in raw_rows]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate source field/target partition")
    reader = _reader(texts["02_source_mapping_registry_inputs.py"])
    selected_counts = []
    for original,route in zip(profiles,EXPECTED_ROUTES):
        if (original.get("MAPPING_FILE") != MAPPING_FILE
                or original.get("MAPPING_SOURCE_COLUMN") != "SOURCE_KEY"
                or original.get("MAPPING_SOURCE_VALUE") != route["source_key"]
                or tuple(original.get("MODEL_BINDINGS",())) != (route["model"],)):
            raise ValueError("Source binding or model ownership changed")
        profile = dict(original,MAPPING_FILE=str(root/MAPPING_FILE))
        rows = reader(profile)
        aliases = {s.upper() for s in config["MODEL_CONTRACTS"][route["model"]]["MODEL_ALIASES"]}
        selected = [r for r in rows if r.get("EXECUTION_STATUS") == "APPROVED"
                    and str(r.get("OSCAL_MODEL") or "").upper() in aliases]
        if len(rows) != route["input_rows"] or len(selected) != route["selected_rows"]:
            raise ValueError("Mapping selection changed")
        selected_counts.append(len(selected))
    return {"status":"VERIFIED","input_rows":143,"selected_rules":126,
            "selected_rule_counts":selected_counts,"runtime_cells":7,
            "warehouse_contacted":False,"warehouse_installation":"NOT_VERIFIED"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_release(args.directory),indent=2))

if __name__ == "__main__":
    main()
