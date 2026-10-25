# REVIEW_ONLY Source Two preservation candidate; no warehouse write authorization.
# %% Cell 7 - Run the mapping
OSCAL_LOAD_MODE = "PREVIEW"  # Review candidate: COMMIT is explicitly blocked.

# The policy allowlist is release data approved independently of live inputs.
# Empty by default: explicit per-delta approval remains the backward-compatible API.
OSCAL_DAILY_WRITE_POLICY = None
OSCAL_APPROVED_DAILY_WRITE_POLICIES = {}
# Optional finite release variants are authored and verified outside the job.
OSCAL_APPROVED_DAILY_WRITE_POLICY_VARIANTS = {}
_OSCAL_DAILY_POLICY_SCHEMA = "oscal-daily-insert-update-policy-v1"
_OSCAL_DAILY_POLICY_VOLATILE_CONFIG = frozenset({
    "RUN_ID", "EXECUTE_WRITES", "EXPECTED_SOURCE_RECORDS", "LINEAGE_GAP_COUNT",
    "APPROVED_COMMIT_CHANGE_ENVELOPE", "APPROVED_COMMIT_RETIREMENT_COUNTS",
})


def _daily_policy_typed(value):
    """Canonicalize policy metadata strictly, without stringifying unknown objects."""
    import datetime as _datetime
    import decimal as _decimal
    import math as _math
    import uuid as _uuid

    kind = type(value)
    if value is None:
        return ["null"]
    if kind is bool:
        return ["bool", value]
    if kind is int:
        return ["int", str(value)]
    if kind is str:
        return ["str", value]
    if kind is float:
        if not _math.isfinite(value):
            raise ValueError("DAILY_WRITE_POLICY_NONFINITE_METADATA")
        return ["float", value.hex()]
    if kind is _decimal.Decimal:
        if not value.is_finite():
            raise ValueError("DAILY_WRITE_POLICY_NONFINITE_METADATA")
        return ["decimal", str(value)]
    if kind in (_datetime.datetime, _datetime.date, _datetime.time):
        return [kind.__name__, value.isoformat()]
    if kind is _datetime.timedelta:
        return ["timedelta", value.days, value.seconds, value.microseconds]
    if kind is _uuid.UUID:
        return ["uuid", value.hex]
    if kind is bytes:
        return ["bytes", value.hex()]
    if kind is dict:
        if any(type(key) is not str for key in value):
            raise ValueError("DAILY_WRITE_POLICY_METADATA_KEYS_INVALID")
        return ["dict", [[key, _daily_policy_typed(value[key])] for key in sorted(value)]]
    if kind in (list, tuple):
        return [kind.__name__, [_daily_policy_typed(item) for item in value]]
    if kind in (set, frozenset):
        items = [_daily_policy_typed(item) for item in value]
        return [kind.__name__, sorted(items, key=lambda item: json.dumps(
            item, sort_keys=True, separators=(",", ":"), allow_nan=False))]
    raise ValueError("DAILY_WRITE_POLICY_METADATA_TYPE_UNSUPPORTED")


def _daily_write_policy_metadata(source_inputs, mapping_contexts):
    """Construct the unchanged pinned release metadata, without reading source rows."""

    runtime = {
        "mapper": getattr(build_oscal_graph, "_oscal_mapper_release", None),
        "loader": getattr(validate_and_load_oscal, "_oscal_loader_release", None),
    }
    if runtime != {
        "mapper": "lean-csv-registry-v18-native-catalog-bulk",
        "loader": "oscal-lean-daily-v3.4.1-required-approval",
    }:
        raise ValueError("DAILY_WRITE_POLICY_RUNTIME_MISMATCH")
    routes, seen = [], set()
    for context in mapping_contexts:
        config = context["config"]
        key = (context["source_key"], config["OSCAL_MODEL"])
        if key in seen or key[0] not in source_inputs:
            raise ValueError("DAILY_WRITE_POLICY_ROUTE_BINDING_INVALID")
        seen.add(key)
        if (config.get("ENABLE_APPROVED_SSP_CIA_RETIREMENT", False) is not False
                or config.get("ONE_TIME_RETIREMENT_SPEC")):
            raise ValueError("DAILY_WRITE_POLICY_RETIREMENT_DISABLED")
        plan = context["compiled_plan"]
        fingerprint = plan.get("mapping_fingerprint")
        if (not isinstance(fingerprint, str) or len(fingerprint) != 64
                or any(char not in "0123456789abcdef" for char in fingerprint)):
            raise ValueError("DAILY_WRITE_POLICY_FINGERPRINT_INVALID")
        selected = context["routing_report"].get("SELECTED_ROWS")
        if type(selected) is not int or selected <= 0 or selected != len(context["mapping_rows"]):
            raise ValueError("DAILY_WRITE_POLICY_SELECTION_INVALID")
        expected_by_path = {}
        for row in context["mapping_rows"]:
            expected_by_path.setdefault(row["OWNER_ELEMENT_PATH"], []).append(row)
        if _daily_policy_typed(context.get("mappings_by_path")) != _daily_policy_typed(expected_by_path):
            raise ValueError("DAILY_WRITE_POLICY_MAPPING_INDEX_MISMATCH")
        effective_config = {name: value for name, value in config.items()
                            if name not in _OSCAL_DAILY_POLICY_VOLATILE_CONFIG}
        if plan.get("native_catalog") is not None:
            if (config["OSCAL_MODEL"] != "CATALOG"
                    or ("NATIVE_CATALOG_EDGE_POLICY" in config and
                        config["NATIVE_CATALOG_EDGE_POLICY"] != "catalog-control-owner-edge-v1")):
                raise ValueError("DAILY_WRITE_POLICY_NATIVE_EDGE_POLICY_MISMATCH")
            # Cell4 deterministically enables this accepted loader identity rule.
            # Bind the effective execution policy before and after graph building.
            effective_config["NATIVE_CATALOG_EDGE_POLICY"] = "catalog-control-owner-edge-v1"
        lookups = source_inputs[key[0]].get("lookups", {})
        contracts = {name: value for name, value in lookups.items()
                     if name.endswith("_contract")}
        routes.append({
            "source_key": key[0], "model": key[1],
            "config": effective_config,
            "compiled_plan": plan, "mapping_rows": context["mapping_rows"],
            "registry": _canonical_registry_rows(None, key[1], context),
            "model_contract": context["model_contract"],
            "selected_mapping_rows": selected,
            "lookup_contracts": contracts,
        })
    routes.sort(key=lambda route: (route["source_key"], route["model"]))
    return {
        "schema": _OSCAL_DAILY_POLICY_SCHEMA, "runtime": runtime, "routes": routes,
        "operations": ("INSERT", "UPDATE"), "retirements": False,
    }


def _daily_write_policy_binding(source_inputs, mapping_contexts):
    """Hash the same canonical payload; diagnostics never extend its authorization."""
    return _daily_policy_hash(_daily_write_policy_metadata(source_inputs, mapping_contexts))

# Hash-only metadata is diagnostic evidence, never authorization.
_OSCAL_DAILY_DIAGNOSTIC_SCHEMA = "oscal-daily-policy-components-v1"
_OSCAL_DAILY_DIAGNOSTIC_KEYS = frozenset({
    "OSCAL_VERSION", "SSP_DOCUMENT_VERSION", "IDENTITY_VERSION", "ASSESSMENT_TASK_TITLE",
    "ASSESSMENT_TASK_TYPE", "ELEMENT_REGISTRY_TABLE", "ENABLE_APPROVED_SSP_CIA_RETIREMENT",
    "OSCAL_MODEL", "ROOT_PATH", "ROOT_ELEMENT_TYPE", "STORAGE_CONTRACT",
    "SOURCE_SYSTEM_NAME", "SOURCE_TABLE_NAME", "RAW_TABLE", "TARGET_DIM", "TARGET_FACT",
    "DIM_PK_COLUMN", "FACT_PK_COLUMN", "NATIVE_CATALOG_EDGE_POLICY", "ONE_TIME_RETIREMENT_SPEC",
    "version", "release", "elements", "mappings", "reference_groups", "mapping_fingerprint",
    "options", "report", "native_catalog", "owner_procedure_props", "scalar_array_properties",
    "ELEMENTS", "ELEMENT_PATHS", "REFERENCE_GROUPS", "REPORT", "RUNTIME_OPTIONS",
    "LOOKUP_GROUPS", "UNREVIEWED_ROWS", "ROOT_ELEMENT_TYPE", "STORAGE_CONTRACT",
    "component_contract", "joined_contract", "native_control_contract",
    "native_control_guid_contract", "owner_procedure_guid_contract",
    "element_path", "element_type", "parent_path", "level", "process_order", "is_collection",
    "schema", "runtime", "operations", "retirements",
})


def _daily_policy_hash(value):
    import hashlib as _hashlib
    return _hashlib.sha256(json.dumps(
        _daily_policy_typed(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _daily_diagnostic_key(name):
    return name if name in _OSCAL_DAILY_DIAGNOSTIC_KEYS else "sha256:" + _daily_policy_hash(name)


def _daily_policy_component_hashes(metadata):
    """Return metadata hashes and approved structural key labels; never values."""
    result = {
        "schema": _OSCAL_DAILY_DIAGNOSTIC_SCHEMA,
        "binding_sha256": _daily_policy_hash(metadata),
        "global": {name: _daily_policy_hash(value)
                   for name, value in metadata.items() if name != "routes"},
        "routes": {},
    }
    for route in metadata["routes"]:
        token = _daily_policy_hash((route["source_key"], route["model"]))
        keys = {}
        for name in ("config", "compiled_plan", "model_contract", "lookup_contracts"):
            keys[name] = {_daily_diagnostic_key(key): _daily_policy_hash(value)
                          for key, value in route[name].items()}
        registry = {}
        for row in route["registry"]:
            entry = _daily_policy_hash(row["element_path"])
            registry[entry] = {_daily_diagnostic_key(key): _daily_policy_hash(value)
                               for key, value in row.items()}
        result["routes"][token] = {
            "components": {name: _daily_policy_hash(value) for name, value in route.items()},
            "keys": keys, "registry_entries": registry,
        }
    return result


def _daily_policy_mismatch_diagnostics(pinned, observed, metadata):
    """Expose only hashes and allowlisted structural labels after a pinned mismatch."""
    result = {"schema": _OSCAL_DAILY_DIAGNOSTIC_SCHEMA,
              "expected_binding_sha256": pinned, "observed_binding_sha256": observed}
    try:
        result.update(status="BINDING_MISMATCH",
                      observed_components=_daily_policy_component_hashes(metadata))
    except Exception:
        # Never expose raw metadata or exception payloads if diagnostics fail.
        result["status"] = "COMPONENT_DIAGNOSTICS_UNAVAILABLE"
    return result


def _daily_require_write_policy(source_inputs, mapping_contexts, policy):
    """Current metadata cannot create or extend its own standing authorization."""
    if (type(policy) is not dict or set(policy) != {"policy_id"}
            or type(policy["policy_id"]) is not str or not policy["policy_id"]):
        raise ValueError("DAILY_WRITE_POLICY_REQUIRED_OR_INVALID")
    approved = OSCAL_APPROVED_DAILY_WRITE_POLICIES.get(policy["policy_id"])
    if (type(approved) is not dict
            or set(approved) != {"enabled", "binding_sha256"}
            or approved.get("enabled") is not True):
        raise ValueError("DAILY_WRITE_POLICY_NOT_ACTIVE")
    pinned = approved["binding_sha256"]
    if (type(pinned) is not str or len(pinned) != 64
            or any(char not in "0123456789abcdef" for char in pinned)):
        raise ValueError("DAILY_WRITE_POLICY_PIN_INVALID")
    variants = OSCAL_APPROVED_DAILY_WRITE_POLICY_VARIANTS
    if type(variants) is not dict:
        raise ValueError("DAILY_WRITE_POLICY_VARIANTS_INVALID")
    alternate = variants.get(pinned, ())
    if (type(alternate) is not tuple or len(alternate) > 1
            or any(type(value) is not str or len(value) != 64
                   or value == pinned
                   or any(char not in "0123456789abcdef" for char in value)
                   for value in alternate)):
        raise ValueError("DAILY_WRITE_POLICY_VARIANTS_INVALID")
    metadata = _daily_write_policy_metadata(source_inputs, mapping_contexts)
    observed = _daily_policy_hash(metadata)
    if observed not in (pinned, *alternate):
        error = ValueError("DAILY_WRITE_POLICY_BINDING_MISMATCH")
        error.daily_write_policy_diagnostics = _daily_policy_mismatch_diagnostics(
            pinned, observed, metadata)
        raise error
    result = {"policy_id": policy["policy_id"], "binding_sha256": observed,
              "status": "VALIDATED", "operations": ["INSERT", "UPDATE"],
              "retirements_allowed": False}
    if observed != pinned:
        result["primary_binding_sha256"] = pinned
    return result


def _daily_preview_approval(preview, config):
    """Authorize only this invocation's successful, non-retiring preview delta."""
    if (preview.get("status") != "PREVIEW_PASSED_NO_TARGET_DML"
            or preview.get("mode") != "PREVIEW"
            or preview.get("validation_passed") is not True
            or preview.get("storage_verified") is not True
            or preview.get("pre_write_validation_passed") is not True
            or any(preview.get(name) is not False for name in (
                "writes_executed", "persisted", "committed", "target_dml_attempted"))):
        raise ValueError("DAILY_WRITE_POLICY_PREVIEW_REQUIRED")
    approved_config = dict(
        config,
        APPROVED_COMMIT_CHANGE_ENVELOPE=copy.deepcopy(preview.get("expected_changes")),
        APPROVED_COMMIT_RETIREMENT_COUNTS=copy.deepcopy(preview.get("approved_retirement")),
    )
    _load_require_approved_commit_envelope({
        "changes": preview.get("expected_changes"),
        "retirement_counts": preview.get("approved_retirement"),
    }, approved_config)
    if approved_config["APPROVED_COMMIT_RETIREMENT_COUNTS"] != {
            "nodes": 0, "edges": 0, "source_records": 0}:
        raise ValueError("DAILY_WRITE_POLICY_RETIREMENT_BLOCKED")
    return approved_config



class PipelineError(ValueError):
    def __init__(self, report):
        super().__init__("OSCAL pipeline stopped; inspect OSCAL_PIPELINE_REPORT")
        self.report = report


def run_oscal_mapping(source_df, canonical_mapping_df, element_registry_df, config, context=None):
    """Build the graph, validate it, and load only when this run enables writes."""
    nodes, edges = build_oscal_graph(
        source_df, canonical_mapping_df, element_registry_df, config["OSCAL_MODEL"],
        config["SOURCE_SYSTEM_NAME"], config["SOURCE_TABLE_NAME"], context=context,
    )
    config = dict(config)
    if "EXPECTED_SOURCE_RECORDS" not in config:
        config["EXPECTED_SOURCE_RECORDS"] = source_df.count()
    result = validate_and_load_oscal(nodes, edges, config)
    return nodes, edges, result


def run_oscal_pipeline(source_inputs, mapping_contexts, load_mode="PREVIEW", daily_write_policy=None):
    """Preview every route before the first commit. Transactions are per route."""
    report = {"mode": load_mode, "status": "RUNNING", "groups": [],
              "writes_executed": False, "commit_attempted": False}
    graphs, active = {}, None
    try:
        if load_mode != "PREVIEW":
            raise ValueError("REVIEW_CANDIDATE_PREVIEW_ONLY")
        if load_mode not in {"PREVIEW", "COMMIT"} or not mapping_contexts:
            raise ValueError("Choose PREVIEW or COMMIT and at least one mapping route")
        if getattr(validate_and_load_oscal, "_oscal_loader_release", None) != "oscal-lean-daily-v3.4.1-required-approval":
            raise ValueError("Run the matching Cell 6 before Cell 7")
        if getattr(build_oscal_graph, "_oscal_mapper_release", None) != "lean-csv-registry-v18-native-catalog-bulk":
            raise ValueError("Run the matching Cell 5 before Cell 7")
        routes = {}
        for context in mapping_contexts:
            config = context["config"]
            active = (context["source_key"], config["OSCAL_MODEL"])
            if active in routes or active[0] not in source_inputs:
                raise ValueError("Duplicate mapping route or missing source input")
            if context["routing_report"]["STATUS"] != "READY" or not context["mapping_rows"]:
                # Preserve Cell 3's actual reason in the existing pipeline report.
                # Counts/field metadata only; no source records or another read.
                report["routing_report"] = copy.deepcopy(context["routing_report"])
                reason = report["routing_report"].get("CONTRACT_ERROR") or json.dumps(
                    report["routing_report"].get("REASON_COUNTS", {}), sort_keys=True)
                raise ValueError("Mapping route is blocked or has no approved rows; " + reason)
            if config.get("EXECUTE_WRITES") is not False:
                raise ValueError("Keep shared EXECUTE_WRITES false; choose the Cell 7 load mode")
            if load_mode == "COMMIT" and (config.get("STORAGE_CONTRACT") or {}).get("VERIFIED") is not True:
                raise ValueError("Every selected route needs a verified destination before COMMIT")
            if active == ("source-one", "SSP") and config.get(
                    "ENABLE_APPROVED_SSP_CIA_RETIREMENT", False):
                # Fail before graph construction if an old uploaded mapping CSV
                # compiled without the approved direct-null CIA member contract.
                impact = context.get("compiled_plan", {}).get("elements", {}).get(
                    "system-security-plan.system-characteristics.security-impact-level", {})
                if impact.get("parameters", {}).get("preserve_explicit_null_members") is not True:
                    raise ValueError("SSP_CIA_DIRECT_MAPPING_CSV_NOT_ACTIVE")
            routes[active] = context
        policy = (_daily_require_write_policy(source_inputs, mapping_contexts, daily_write_policy)
                  if daily_write_policy is not None else None)
        if policy is not None:
            report["daily_write_policy"] = policy
        for active, original in routes.items():
            context = copy.deepcopy(original)
            source = source_inputs[active[0]]
            context["lookups"] = source.get("lookups", {})
            expected = source.get("selection", {}).get("SELECTED_ROWS")
            if expected is not None:
                context["config"]["EXPECTED_SOURCE_RECORDS"] = expected
            nodes, edges, result = run_oscal_mapping(source["source_df"], None, None, context["config"], context)
            graphs[active] = {"nodes": nodes, "edges": edges, "context": context}
            report["groups"].append({"source": active[0], "model": active[1], "load": result,
                                     "mapping_fingerprint": context["compiled_plan"]["mapping_fingerprint"],
                                     "lineage": {key: value for key, value in context["graph_report"].items()
                                                 if key.startswith("LINEAGE_")},
                                     "native_catalog": {key: value for key, value in context["graph_report"].items()
                                                        if key.startswith("NATIVE_CATALOG_")},
                                     "security_impact": {key: value for key, value in context["graph_report"].items()
                                                         if key.startswith("SECURITY_IMPACT_")}})
        if load_mode == "COMMIT":
            if any(graph["context"]["config"].get("LINEAGE_GAP_COUNT", 0) for graph in graphs.values()):
                raise ValueError("LINEAGE_COVERAGE_GAPS: review the graph lineage report before COMMIT")
            if policy is not None:
                # The pinned standing policy approves only these same invocation graphs.
                # It never reuses a previous run or lifts the no-retirement boundary.
                rechecked_policy = _daily_require_write_policy(
                    source_inputs, [graph["context"] for graph in graphs.values()],
                    daily_write_policy)
                if rechecked_policy["binding_sha256"] != policy["binding_sha256"]:
                    raise ValueError("DAILY_WRITE_POLICY_VARIANT_CHANGED_DURING_RUN")
                for group in report["groups"]:
                    active = (group["source"], group["model"])
                    graph = graphs[active]
                    graph["context"]["config"] = _daily_preview_approval(
                        group["load"], graph["context"]["config"])
            # Review every route against its external or scoped policy approval before any route writes.
            # Global CONFIG edits cannot substitute for approval in a compiled context.
            for group in report["groups"]:
                active = (group["source"], group["model"])
                graph = graphs[active]
                preview = group["load"]
                _load_require_approved_commit_envelope(
                    {"changes": preview.get("expected_changes"),
                     "retirement_counts": preview.get("approved_retirement")},
                    graph["context"]["config"],
                )
            for group in report["groups"]:
                active = (group["source"], group["model"])
                graph = graphs[active]
                report["commit_attempted"] = True
                result = validate_and_load_oscal(graph["nodes"], graph["edges"],
                                                dict(graph["context"]["config"], EXECUTE_WRITES=True))
                group["load"] = result
                report["writes_executed"] |= result["writes_executed"]
        report["status"] = "COMMITTED_AND_VERIFIED" if load_mode == "COMMIT" else "PREVIEW_COMPLETE"
        return graphs, report
    except BaseException as error:
        details = getattr(error, "details", {})
        # Cell 4's own CatalogControlError contains a constant, value-free reason.
        # Do not redact it just because it subclasses ValueError; other errors stay protected.
        native_reason = type(error) is globals().get("CatalogControlError")
        report.update(status="COMMIT_FAILED_REVIEW_REQUIRED" if report["commit_attempted"] else "FAILED_BEFORE_COMMIT",
                      failed_route=active, error_type=type(error).__name__,
                      error_message=(str(error) if type(error) is ValueError or isinstance(error, LoadError) or native_reason
                                     else "Operation failed; inspect protected runtime logs."), load_error=details)
        report["writes_executed"] |= details.get("writes_executed") is True
        if (type(error) is ValueError and error.args == ("DAILY_WRITE_POLICY_BINDING_MISMATCH",)
                and hasattr(error, "daily_write_policy_diagnostics")):
            report["daily_write_policy_diagnostics"] = error.daily_write_policy_diagnostics
            report["failed_route"] = None  # This check compares the complete route set.
        raise PipelineError(report) from None


MODEL_GRAPHS = PIPELINE_REPORT = None
try:
    MODEL_GRAPHS, PIPELINE_REPORT = run_oscal_pipeline(
        SOURCE_INPUTS, MAPPING_CONTEXTS, OSCAL_LOAD_MODE,
        daily_write_policy=OSCAL_DAILY_WRITE_POLICY)
except PipelineError as error:
    PIPELINE_REPORT = error.report
    raise
finally:
    print("OSCAL_PIPELINE_REPORT")
    print(json.dumps(PIPELINE_REPORT, indent=2, default=str))
