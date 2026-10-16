# %% Source Two Catalog Back Matter: one-time input-structure inspection
# 2026-10-16. Run ONE new cell in the existing Snowflake notebook.
# Reads only retained SOURCE_INPUTS frames. No target/registry writes,
# no pipeline execution, no COMMIT, and no changes to mapper configuration.
# Prints member names/types/counts, NOT URLs, record IDs or attachment contents.

def inspect_catalog_back_matter(namespace=None):
    import base64
    import json
    import re
    from collections import Counter
    from decimal import Decimal
    from urllib.parse import urlsplit

    env = globals() if namespace is None else namespace
    source = (env.get("SOURCE_INPUTS") or {}).get("source-two-source")
    if not isinstance(source, dict):
        raise RuntimeError("BACK_MATTER_INPUTS_MISSING: retain the current notebook; do not rerun COMMIT")
    joined = (source.get("lookups") or {}).get("joined_sources", {})
    scopes = [
        ("Source", source.get("source_df"), ("SOURCE_LINKS", "TOPIC_REFERENCES", "ATTACHMENTS")),
        ("Topic", joined.get("topics"), ("ATTACHMENTS",)),
        ("Section", joined.get("sections"), ("ATTACHMENTS",)),
        ("Sub-Section", joined.get("subsections"), ("ATTACHMENTS",)),
    ]
    if any(frame is None or not hasattr(frame, "select") or not hasattr(frame, "to_local_iterator")
           for _, frame, _ in scopes):
        raise RuntimeError("BACK_MATTER_RETAINED_FRAME_MISSING: no source reload attempted")
    missing = object()
    max_depth, max_signatures = 6, 200

    def kind(value):
        if value is missing:
            return "MISSING_KEY"
        if value is None:
            return "JSON_NULL"
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, (int, float, Decimal)):
            return "NUMBER"
        if isinstance(value, dict):
            return "OBJECT" if value else "EMPTY_OBJECT"
        if isinstance(value, list):
            return "ARRAY" if value else "EMPTY_ARRAY"
        if isinstance(value, str):
            return "TEXT" if value.strip() else "EMPTY_TEXT"
        return "OTHER_TYPE"

    def text_form(value):
        text = value.strip()
        if not text:
            return "EMPTY_TEXT", None
        # Parsing identifies structure only; no source is transformed or fetched.
        if text[:1] in ("{", "[") and len(text) <= 1048576:
            try:
                decoded = json.loads(text)
                if isinstance(decoded, (dict, list)):
                    return "JSON_ENCODED_" + kind(decoded), decoded
            except (ValueError, TypeError):
                pass
        try:
            uri = urlsplit(text)
            if re.search(r"\s", text):
                return "OTHER_TEXT", None
            if uri.scheme.lower() in ("http", "https") and uri.hostname:
                return "HTTP_URL_SHAPED_TEXT", None
            if uri.scheme:
                return "OTHER_URI_SCHEME_TEXT", None
            if text.startswith(("/", "./", "../", "#")):
                return "RELATIVE_REFERENCE_SHAPED_TEXT", None
        except ValueError:
            return "INVALID_URI_SHAPED_TEXT", None
        if 64 <= len(text) <= 1048576 and len(text) % 4 == 0:
            try:
                base64.b64decode(text, validate=True)
                return "BASE64_SYNTAX_CANDIDATE_NOT_CONTENT_PROOF", None
            except (ValueError, TypeError):
                pass
        return "OTHER_TEXT", None

    def inspect(value, path, depth, counts, notices):
        signature = (path, kind(value))
        if signature not in counts and len(counts) >= max_signatures:
            notices["signature_limit_skipped"] += 1
            return
        counts[signature] += 1
        if depth >= max_depth and isinstance(value, (dict, list)) and value:
            notices["depth_limit_skipped"] += 1
            return
        if isinstance(value, dict):
            for key, item in value.items():
                # Numeric/dynamic-looking keys are suppressed from output.
                safe = isinstance(key, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ -]{0,79}", key)
                label = key if safe else "<redacted-key>"
                if not safe:
                    notices["redacted_keys"] += 1
                inspect(item, path + "[" + json.dumps(label) + "]", depth + 1, counts, notices)
        elif isinstance(value, list):
            for item in value:
                inspect(item, path + "[]", depth + 1, counts, notices)
        elif isinstance(value, str) and value.strip():
            form, decoded = text_form(value)
            form_signature = (path, form)
            if form_signature in counts or len(counts) < max_signatures:
                counts[form_signature] += 1
            else:
                notices["signature_limit_skipped"] += 1
            if decoded is not None:
                if depth < max_depth:
                    inspect(decoded, path + "::decoded-json", depth + 1, counts, notices)
                else:
                    notices["depth_limit_skipped"] += 1

    output = {"status": "CATALOG_BACK_MATTER_INPUT_STRUCTURE", "target_writes": False,
              "mapping_changes": False, "fields": []}
    for level, frame, fields in scopes:
        root_counts = {field: Counter() for field in fields}
        shapes = {field: Counter() for field in fields}
        notices = {field: Counter() for field in fields}
        record_count = 0
        for record in frame.select("CURATED_JSON").to_local_iterator():
            doc = record["CURATED_JSON"]
            if hasattr(doc, "as_dict"):
                doc = doc.as_dict(recursive=True)
            if isinstance(doc, str):
                try:
                    doc = json.loads(doc)
                except (ValueError, TypeError):
                    raise RuntimeError("BACK_MATTER_INVALID_CURATED_JSON: " + level) from None
            if not isinstance(doc, dict):
                raise RuntimeError("BACK_MATTER_CURATED_JSON_NOT_OBJECT: " + level)
            record_count += 1
            for field in fields:
                value = doc.get(field, missing)  # Exact key, never a guessed alias.
                root_counts[field][kind(value)] += 1
                if value is not missing:
                    inspect(value, "$", 0, shapes[field], notices[field])
        if not record_count:
            raise RuntimeError("BACK_MATTER_NO_RETAINED_ROWS: " + level)
        for field in fields:
            output["fields"].append({
                "level": level, "field": field, "records_read": record_count,
                "source_shapes": dict(sorted(root_counts[field].items())),
                "member_shapes": [{"path": path, "type": dtype, "occurrences": n}
                                  for (path, dtype), n in sorted(shapes[field].items())],
                "inspection_limits": dict(sorted(notices[field].items())),
            })
    print(json.dumps(output, indent=2))
    return output


CATALOG_BACK_MATTER_INPUTS = inspect_catalog_back_matter()
