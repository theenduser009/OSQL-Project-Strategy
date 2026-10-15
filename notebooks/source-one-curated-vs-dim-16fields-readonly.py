# Source One: CURATED_JSON versus persisted OSCAL DIM, 2026-10-15
# Read-only. Run in ONE NEW PYTHON cell of the active Snowflake notebook.
# No COMMIT, MERGE, target writes, file uploads, or new views.
# This reports PERSISTED DIM, not the uncommitted PREVIEW candidate.
import collections as _qcol
import copy as _qcopy
import json as _qjson
import importlib as _qimport
datetime = _qimport.import_module("datetime")

FIELDS = ("POAMS","AUTHORIZATION_PACKAGE_NAME","ACRONYM","OPERATIONAL_STATUS",
          "AUTHORIZATION_DECISION","ATOIATO_DATE","AUTHORIZATION_PACKAGE_SUBMIT_DATE",
          "ATOIATO_EXPIRATION_DATE","WORKFLOW_STATUS","INFORMATION_OWNER_IO",
          "AUTHORIZING_OFFICIAL_AO","LEGACY_SAP_ID","ALTERNATE_SYSTEM_ADMINISTRATOR_SA",
          "SYSTEM_ADMINISTRATOR_SA","ENTITY","BUSINESS")
MAX_SAMPLES = 12
src = SOURCE_INPUTS["source-one"]
ctxs = [c for c in MAPPING_CONTEXTS if c["source_key"] == "source-one"
        and c["config"]["OSCAL_MODEL"] == "SSP"]
if len(ctxs) != 1:
    raise RuntimeError("Requires one compiled Source One SSP context")
ctx = _qcopy.deepcopy(ctxs[0])
ctx["lookups"] = src.get("lookups", {})
ctx["graph_report"] = {"STATUS":"QA", "MAPPED_VALUES":0, "MISSING_VALUES":0}
rules = [r for r in MAPPING_INPUTS["source-one"] if r.get("SOURCE_FIELD_NAME") in FIELDS
         and r.get("EXECUTION_STATUS") == "APPROVED"]
if len(rules) != 17:
    raise RuntimeError("Expected 17 approved mapping occurrences; check uploaded CSV")
compiled = {(r["SOURCE_FIELD_NAME"],r["CANONICAL_ELEMENT_PATH"]):r
            for r in ctx["mapping_rows"]}

def printable(x):
    if x is SKIP_VALUE: return "<ABSENT>"
    return _qjson.dumps(x, default=str, ensure_ascii=False, sort_keys=True)

def payload(x):
    if hasattr(x, "as_dict"): x = x.as_dict(recursive=True)
    if isinstance(x,str):
        try: return _qjson.loads(x)
        except ValueError: return x
    return x

def source_state(x):
    return ("ABSENT" if x is SKIP_VALUE else "NULL" if x is None
            else "EMPTY" if x in ("",[],{}) else "POPULATED")

counts = {f:_qcol.Counter() for f in FIELDS}
examples = {f:{"POPULATED":[],"NULL":[],"EMPTY":[],"ABSENT":[]} for f in FIELDS}
total = 0
for item in src["source_df"].to_local_iterator():
    total += 1
    sid = str(item["SOURCE_RECORD_ID"])
    obj = _metadata_parse(item,ctx)
    for field in FIELDS:
        v = resolve_json_path(obj,field,default=SKIP_VALUE)
        state = source_state(v)
        counts[field][state] += 1
        if len(examples[field][state]) < MAX_SAMPLES:
            examples[field][state].append((sid,obj))
chosen = {f:(examples[f]["POPULATED"]+examples[f]["NULL"]
              +examples[f]["EMPTY"]+examples[f]["ABSENT"])[:MAX_SAMPLES] for f in FIELDS}
ids = sorted({sid for recs in chosen.values() for sid,_ in recs})
identifiers = ",".join("'" + x.replace("'","''") + "'" for x in ids)
targets = {}
errors = {}
for model in ("SSP","ASSESSMENT_RESULTS","POAM"):
    s = MODEL_CONTRACTS[model]["STORAGE_CONTRACT"]
    dim,fact,pk = s["TARGET_DIM"],s["TARGET_FACT"],s["DIM_PK_COLUMN"]
    stmt = f"""SELECT d.SOURCE_RECORD_ID CID, d.ELEMENT_TYPE ET,
        d.METADATA_JSON JSON_DATA, p.ELEMENT_TYPE PARENT_ET
      FROM {dim} d LEFT JOIN {fact} f
        ON f.FK_TARGET_ELEMENT_HASH=d.{pk}
      LEFT JOIN {dim} p ON p.{pk}=f.FK_SOURCE_ELEMENT_HASH
      WHERE d.SOURCE_RECORD_ID IN ({identifiers})
      AND d.SOURCE_SYSTEM_NAME='ARCHER'
      AND d.SOURCE_TABLE_NAME='ARCHER_CONTENT_AUTHORIZATION_PACKAGE_RAW'
      AND d.ELEMENT_TYPE IN ('props','metadata','system-characteristics',
                             'responsible-parties','poam-items')"""
    try:
        targets[model] = _qcol.defaultdict(list)
        for r in session.sql(stmt).to_local_iterator():
            j = payload(r["JSON_DATA"])
            if isinstance(j,dict):
                targets[model][str(r["CID"])].append((r["ET"],r["PARENT_ET"],j))
    except Exception as exc:
        errors[model] = type(exc).__name__

def actual_rows(model,path,sid,field,role):
    if model in errors: return None
    found=[]
    for typ,parent,j in targets.get(model,{}).get(sid,()):
        if path.endswith("props[]"):
            wantparent = "results" if model=="ASSESSMENT_RESULTS" else "system-characteristics"
            if typ=="props" and parent==wantparent and j.get("name")==_stable_property_name(field):
                found.append(j.get("value"))
        elif path.endswith("responsible-parties[]"):
            if typ=="responsible-parties" and parent=="metadata" and j.get("role-id")==role:
                found.append(j)
        elif path.endswith("poam-items[]"):
            if typ=="poam-items" and parent=="plan-of-action-and-milestones":
                found.append(j)
        elif ".system-characteristics." in path and typ=="system-characteristics":
            x=j
            for part in path.split(".system-characteristics.",1)[1].split("."):
                x=x.get(part,SKIP_VALUE) if isinstance(x,dict) else SKIP_VALUE
            if x is not SKIP_VALUE: found.append(x)
        elif ".metadata." in path and typ=="metadata":
            x=j.get(path.split(".metadata.",1)[1],SKIP_VALUE)
            if x is not SKIP_VALUE: found.append(x)
    return found

out=[]
tally=_qcol.Counter()
for field in FIELDS:
    for sid,obj in chosen[field]:
        source_value=resolve_json_path(obj,field,default=SKIP_VALUE)
        state=source_state(source_value)
        for rule in (r for r in rules if r["SOURCE_FIELD_NAME"]==field):
            path=rule["OSCAL_ELEMENT_PATH"]
            model=("SSP" if path.startswith("system-security-plan.")
                   else "ASSESSMENT_RESULTS" if path.startswith("assessment-results.")
                   else "POAM")
            got=actual_rows(model,path,sid,field,rule.get("ROLE_ID"))
            cr=compiled.get((field,path))
            expected=SKIP_VALUE
            if cr and not (path.endswith("responsible-parties[]") or path.endswith("poam-items[]")):
                try:
                    expected=_metadata_mapped_value(cr,obj,ctx)
                    if expected is not SKIP_VALUE and path.endswith("props[]"):
                        expected=[None] if expected is None else _oscal_property_values(expected)
                    elif isinstance(expected,dict) and rule["TRANSFORM_ID"]=="status-crosswalk":
                        expected=expected.get("state",SKIP_VALUE)
                except Exception as exc:
                    expected="<TRANSFORM_ERROR_"+type(exc).__name__+">"
            if got is None: status="TARGET_QUERY_FAILED"
            elif path.endswith(("responsible-parties[]","poam-items[]")):
                status="STRUCTURAL_REFERENCE_REVIEW" if got else "STRUCTURAL_DIM_MISSING"
            elif isinstance(expected,str) and expected.startswith("<TRANSFORM_ERROR_"):
                status=expected
            elif expected is SKIP_VALUE and state!="POPULATED":
                status="NO_POPULATED_SOURCE" if not got else "DIM_PRESENT_SOURCE_EMPTY"
            elif expected is SKIP_VALUE:
                status="MODEL_EXPECTED_TRANSFORM_NOT_COMPILED" if got else "DIM_MISSING"
            elif not got:
                status="SOURCE_HAS_VALUE_DIM_MISSING"
            elif path.endswith("props[]"):
                status="MATCH" if sorted(map(printable,expected))==sorted(map(printable,got)) else "VALUE_MISMATCH"
            else:
                status="MATCH" if len(got)==1 and got[0]==expected else "VALUE_MISMATCH"
            tally[status]+=1
            out.append({"CONTENT_ID":sid,"ARCHER_FIELD":field,"MODEL":model,
                        "EXACT_OSCAL_PATH":path,"SOURCE_STATE":state,
                        "CURATED_JSON_VALUE":printable(source_value),
                        "EXPECTED_MAPPED_VALUE":printable(expected),
                        "PERSISTED_DIM_VALUE":printable(got) if got is not None else "<QUERY_FAILED>",
                        "RESULT":status})
summary=[{"ARCHER_FIELD":f,"POPULATED":counts[f]["POPULATED"],
          "NULL":counts[f]["NULL"],"EMPTY":counts[f]["EMPTY"],
          "ABSENT":counts[f]["ABSENT"],"SAMPLE_IDS":len(chosen[f])} for f in FIELDS]
SOURCE_ONE_QA_COVERAGE, SOURCE_ONE_QA_COMPARISON=summary,out
print("SOURCE ONE: 16 fields / 17 mapping occurrences; source records:",total)
print("RESULT COUNTS:",dict(tally))
print("MODEL QUERY ERRORS:",errors)
print("NO DATABASE WRITES. DIM IS PERSISTED, NOT PREVIEW.")
import pandas as _qpd
from IPython.display import display as _qdisplay
print("FULL SOURCE POPULATION (including null/absent cases)")
_qdisplay(_qpd.DataFrame(summary))
print("CONTENT-ID-LEVEL CURATED JSON vs DIM (12 samples per field)")
_qdisplay(_qpd.DataFrame(out))
