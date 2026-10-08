# Source Two Topic: inspect IDs flagged by the conservative mapping preview.
# READ ONLY. Paste into one new Python cell of the existing mapper notebook.
# Snowflake names come from already-loaded Cell 1. No DML, registry or mapper run.
# This checks possible reversible transformations but does NOT select one.
# Actual ID examples are printed in Snowflake only, NOT in this public file.

import json
import re
from collections import Counter, defaultdict

if not all(k in globals() for k in ("session", "SOURCE_FILES")):
    raise RuntimeError("Open the existing mapper notebook with Cell 1 loaded.")

source_profiles = [
    p for p in SOURCE_FILES
    if "CATALOG" in p.get("MODEL_BINDINGS", ()) and p.get("RAW_TABLE")
]
if len(source_profiles) != 1:
    raise RuntimeError("Expected exactly one configured Catalog source profile.")

source_table = source_profiles[0]["RAW_TABLE"]
if not re.fullmatch(
    r"[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*){2}",
    str(source_table)
):
    raise RuntimeError("Unexpected three-part Source RAW table configuration.")
database, schema, basename = source_table.split(".")
if not basename.upper().endswith("_SOURCE_RAW"):
    raise RuntimeError("Unknown Source RAW naming contract.")
topic_name = basename[:-len("_SOURCE_RAW")] + "_TOPIC_RAW"
entity = topic_name.removesuffix("_RAW").rsplit("_", 1)[-1].upper()
topic_table = f"{database}.{schema}.{topic_name}"
field = entity + "_ID"

def sq(v):
    return "'" + str(v).replace("'", "''") + "'"

sample = [
    r.as_dict()
    for r in session.sql(f"""
      SELECT CONTENT_ID::VARCHAR AS CONTENT_ID,
             GET(CURATED_JSON,{sq(field)})::VARCHAR AS RAW_GROUP_ID,
             TYPEOF(GET(CURATED_JSON,{sq(field)})) AS RAW_TYPE
      FROM {topic_table}
      ORDER BY CONTENT_ID::VARCHAR
    """).collect()
]
if not sample:
    raise RuntimeError("No Topic source rows; stop before choosing an ID strategy.")

# Exactly the conservative regex used in the previous read-only preview.
safe = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")

def issues(raw):
    problems = []
    if raw is None or not raw.strip():
        return ["MISSING_OR_BLANK"]
    if raw != raw.strip():
        problems.append("OUTER_WHITESPACE")
    if raw[0].isdigit():
        problems.append("STARTS_WITH_DIGIT")
    elif not re.fullmatch(r"[A-Za-z_]", raw[0]):
        problems.append("UNSUPPORTED_FIRST_CHARACTER")
    if any(ch.isspace() for ch in raw):
        problems.append("WHITESPACE")
    if re.search(r"[^A-Za-z0-9_.-]", raw):
        problems.append("CHARACTERS_OUTSIDE_CONSERVATIVE_PATTERN")
    if any(ord(ch) > 127 for ch in raw):
        problems.append("NON_ASCII")
    return sorted(set(problems)) or ["OTHER_FORMAT"]

def slug_for_review(raw):
    # Illustrative only: replacing characters can change business identity.
    if raw is None:
        return None
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw.strip())
    slug = slug.strip("-.")
    if not slug:
        return None
    if not re.fullmatch(r"[A-Za-z_]", slug[0]):
        slug = "g-" + slug
    return slug if safe.fullmatch(slug) else None

input_ids = []
counts = Counter()
type_counts = Counter()
bad = []
slug_assignments = defaultdict(set)
source_key_assignments = defaultdict(set)
raw_assignments = defaultdict(set)

for r in sample:
    cid = str(r["CONTENT_ID"])
    raw = r["RAW_GROUP_ID"]
    type_counts[str(r["RAW_TYPE"])] += 1
    raw_assignments[raw].add(cid)
    if raw is not None and safe.fullmatch(raw):
        canonical_slug = raw
        canonical_source_key = raw
    else:
        bad_issues = issues(raw)
        counts.update(bad_issues)
        canonical_slug = slug_for_review(raw)
        canonical_source_key = "topic-" + cid
        bad.append({
            "SOURCE_RECORD_ID": cid,
            "RAW_ID": raw,
            "REASONS": bad_issues,
            "POSSIBLE_SLUG": canonical_slug,
            "POSSIBLE_SOURCE_KEY": canonical_source_key
        })
    slug_assignments[canonical_slug].add(cid)
    source_key_assignments[canonical_source_key].add(cid)
    input_ids.append(raw)

def collisions(groups):
    return sorted(
        [(str(name), len(ids)) for name, ids in groups.items() if len(ids) > 1],
        key=lambda item: (-item[1], item[0])
    )

report = {
    "SOURCE_ROWS": len(sample),
    "DISTINCT_RAW_IDS": len(set(input_ids)),
    "RAW_FIELD_TYPES": dict(type_counts),
    "CONSERVATIVE_FORMAT_FLAGGED": len(bad),
    "FLAG_REASONS_OVERLAP": dict(sorted(counts.items())),
    "EXISTING_RAW_ID_DUPLICATE_GROUPS": len(collisions(raw_assignments)),
    "SLUG_ONLY_FOR_FLAGGED_COLLISION_GROUPS": len(collisions(slug_assignments)),
    "SLUG_ONLY_FOR_FLAGGED_BLANK_CANDIDATES": sum(
        1 for x in bad if x["POSSIBLE_SLUG"] is None
    ),
    "SOURCE_RECORD_ID_FALLBACK_COLLISION_GROUPS": len(
        collisions(source_key_assignments)
    ),
    "CASE_INSENSITIVE_RAW_ID_DUPLICATES": len(collisions({
        k: set(r["CONTENT_ID"] for r in sample if
               (r["RAW_GROUP_ID"] or "").lower() == k)
        for k in set((x or "").lower() for x in input_ids)
    }))
}
print("SOURCE TWO TOPIC: RAW ID FORMAT DIAGNOSTIC (NO MAPPING CHANGE)")
print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
print("UP TO 30 FLAGGED ORIGINAL IDs AND TWO UNAPPROVED EXAMPLES:")
for item in bad[:30]:
    print(json.dumps(item, ensure_ascii=False, default=str))
print("FIRST 15 EXAMPLE SLUG COLLISIONS:")
print(json.dumps(collisions(slug_assignments)[:15], ensure_ascii=False))
print("FIRST 15 EXAMPLE SOURCE-KEY FALLBACK COLLISIONS:")
print(json.dumps(collisions(source_key_assignments)[:15], ensure_ascii=False))
print("NOTE: the preview pattern is conservative; a flagged ID is not by")
print("itself proof of NIST schema nonconformance. Do not normalize without")
print("owner review of semantics, 1416-ID uniqueness and downstream references.")
print("DONE: read-only; no mapper, registry, DIM/FACT or mapping CSV writes.")
