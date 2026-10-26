# %% Cell 7 - Run the mapping
OSCAL_LOAD_MODE = "PREVIEW"  # A fresh COMMIT previews all four routes internally.

# Fixed policy literals are supplied only by independently reviewed release authoring.
OSCAL_DAILY_WRITE_POLICY = {"policy_id": "source-two-dev-complete-lifecycle195-daily-v2"}
OSCAL_APPROVED_DAILY_WRITE_POLICIES = {'source-two-dev-complete-lifecycle195-daily-v2': {'enabled': True, 'binding_sha256': 'e30f2ce8bfbf3b21fbe3ff1999c14c24a705a798319908d3b0cf8b145c1905e9'}}
OSCAL_APPROVED_DAILY_WRITE_POLICY_VARIANTS = {'e30f2ce8bfbf3b21fbe3ff1999c14c24a705a798319908d3b0cf8b145c1905e9': ('96724d102efb6aefe3b2b5569cab85b8790cea2d96018b144dcf2979a3722f77',)}
_OSCAL_DAILY_POLICY_SCHEMA = "oscal-source-two-finite-lifecycle-policy-v2"
_OSCAL_DAILY_LIFECYCLE_VERSION = "source-two-source-properties-v2"
_OSCAL_DAILY_ROUTES = frozenset({
    ("source-two-source", "CATALOG"),
    ("source-two-topic", "ASSESSMENT_RESULTS"),
    ("source-two-section", "ASSESSMENT_RESULTS"),
    ("source-two-subsection", "ASSESSMENT_RESULTS"),
})
# These are deployment prerequisites, not claims that a row count proves them.
# The upstream query must supply complete current-state records. Scheduling must
# enforce one writer. The notebook cannot attest either external condition.
OSCAL_SOURCE_INPUT_CONTRACT = {
    "record_semantics": "FULL_RECORD_CURRENT_STATE",
    "missing_field": "OMIT_OWNED_PROPERTY_WITHIN_PRESENT_SOURCE",
    "absent_source_record": "PRESERVE_EXISTING_TARGET",
}
OSCAL_DEPLOYMENT_CONTRACT = {
    "writer_concurrency": "EXCLUSIVE_SINGLE_WRITER_REQUIRED",
    "transaction_boundary": "PER_ROUTE",
    "partial_or_unknown_outcome": "STOP_AND_RECONCILE_NO_BLIND_RETRY",
}
_OSCAL_DAILY_POLICY_VOLATILE_CONFIG = frozenset({
    "RUN_ID", "EXECUTE_WRITES", "EXPECTED_SOURCE_RECORDS", "LINEAGE_GAP_COUNT",
    "APPROVED_COMMIT_CHANGE_ENVELOPE", "APPROVED_COMMIT_RETIREMENT_COUNTS",
    "APPROVED_SOURCE_PROPERTY_LIFECYCLE_VERSION",
    "APPROVED_SOURCE_PROPERTY_LIFECYCLE_CONTRACT_DIGEST",
    "APPROVED_SOURCE_PROPERTY_RETIREMENT_DIGEST",
    "APPROVED_SOURCE_PROPERTY_DELTA_DIGEST",
    "SOURCE_PROPERTY_PROCEDURE_NAMESPACE", "APPROVED_SOURCE_PROPERTY_PROCEDURE_NAMESPACE",
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
        "source_property_lifecycle": getattr(validate_and_load_oscal, "_source_property_lifecycle_version", None),
    }
    if runtime != {
        "mapper": "lean-csv-registry-v18-native-catalog-bulk",
        "loader": "oscal-lean-daily-v3.4.1-required-approval",
        "source_property_lifecycle": _OSCAL_DAILY_LIFECYCLE_VERSION,
    }:
        raise ValueError("DAILY_WRITE_POLICY_RUNTIME_MISMATCH")
    if (set(source_inputs) != {item[0] for item in _OSCAL_DAILY_ROUTES}
            or {(ctx["source_key"], ctx["config"]["OSCAL_MODEL"]) for ctx in mapping_contexts}
            != _OSCAL_DAILY_ROUTES or len(mapping_contexts) != 4):
        raise ValueError("DAILY_WRITE_POLICY_EXACT_FOUR_ROUTES_REQUIRED")
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
        effective = _daily_effective_lifecycle_config(config, key)
        effective_config = {name: value for name, value in effective.items()
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
        "operations": ("INSERT", "UPDATE"),
        "retirements": {"source_route": "EXACT_DECLARED_SOURCE_PROPERTY_LEAVES_ONLY",
                        "other_routes": False},
        "source_input_contract": OSCAL_SOURCE_INPUT_CONTRACT,
        "deployment_contract": OSCAL_DEPLOYMENT_CONTRACT,
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
              "retirements_allowed": "FINITE_SOURCE_PROPERTY_LIFECYCLE_ONLY",
              "external_prerequisites": ["FULL_RECORD_CURRENT_STATE", "EXCLUSIVE_SINGLE_WRITER_REQUIRED"]}
    if observed != pinned:
        result["primary_binding_sha256"] = pinned
    return result



def _daily_effective_lifecycle_config(config, route):
    """Apply the same fixed metadata spec before and after graph construction."""
    result = dict(config)
    if route == ("source-two-source", "CATALOG"):
        spec = _source_property_complete_spec(config)
        if spec.get("version") != _OSCAL_DAILY_LIFECYCLE_VERSION:
            raise ValueError("DAILY_WRITE_POLICY_LIFECYCLE_VERSION_MISMATCH")
        previous = config.get("SOURCE_PROPERTY_LIFECYCLE_SPEC")
        if previous is not None and previous != spec:
            raise ValueError("DAILY_WRITE_POLICY_LIFECYCLE_SPEC_MISMATCH")
        result["SOURCE_PROPERTY_LIFECYCLE_SPEC"] = spec
    elif (config.get("SOURCE_PROPERTY_LIFECYCLE_SPEC") is not None
          or config.get("SOURCE_PROPERTY_PROCEDURE_NAMESPACE") is not None):
        raise ValueError("DAILY_WRITE_POLICY_CHILD_LIFECYCLE_FORBIDDEN")
    return result


def _daily_preview_context(preview, config):
    """Retain exact observed lifecycle fields for every pre-write preflight."""
    observed = {
        "changes": preview.get("expected_changes"),
        "retirement_counts": preview.get("approved_retirement"),
    }
    spec = config.get("SOURCE_PROPERTY_LIFECYCLE_SPEC")
    if spec is not None:
        import hashlib as _hashlib
        contract_digest = _hashlib.sha256(json.dumps(
            spec, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
        if (preview.get("source_property_lifecycle_version") != _OSCAL_DAILY_LIFECYCLE_VERSION
                or preview.get("source_property_lifecycle_contract_digest") != contract_digest):
            raise ValueError("DAILY_WRITE_POLICY_PREVIEW_LIFECYCLE_MISMATCH")
        for name in ("source_property_retirement_digest", "source_property_delta_digest"):
            digest = preview.get(name)
            if (type(digest) is not str or len(digest) != 64
                    or any(char not in "0123456789abcdef" for char in digest)):
                raise ValueError("DAILY_WRITE_POLICY_PREVIEW_LIFECYCLE_DIGEST_REQUIRED")
        if (type(config.get("SOURCE_PROPERTY_PROCEDURE_NAMESPACE")) is not str
                or preview.get("source_property_procedure_namespace")
                != config["SOURCE_PROPERTY_PROCEDURE_NAMESPACE"]):
            raise ValueError("DAILY_WRITE_POLICY_PREVIEW_NAMESPACE_MISMATCH")
        observed.update(
            source_property_spec=spec,
            source_property_lifecycle_contract_digest=contract_digest,
            source_property_retirement_digest=preview["source_property_retirement_digest"],
            source_property_delta_digest=preview["source_property_delta_digest"],
            source_property_procedure_namespace=preview.get("source_property_procedure_namespace"),
        )
    else:
        if any(key.startswith("source_property_") for key in preview):
            raise ValueError("DAILY_WRITE_POLICY_CHILD_LIFECYCLE_FORBIDDEN")
        if observed["retirement_counts"] != {"nodes": 0, "edges": 0, "source_records": 0}:
            raise ValueError("DAILY_WRITE_POLICY_CHILD_RETIREMENT_BLOCKED")
    return observed


def _daily_preview_approval(preview, config):
    """Authorize only this invocation's successful fixed-policy preview."""
    if (preview.get("status") != "PREVIEW_PASSED_NO_TARGET_DML"
            or preview.get("mode") != "PREVIEW"
            or preview.get("validation_passed") is not True
            or preview.get("storage_verified") is not True
            or preview.get("pre_write_validation_passed") is not True
            or any(preview.get(name) is not False for name in (
                "writes_executed", "persisted", "committed", "target_dml_attempted"))):
        raise ValueError("DAILY_WRITE_POLICY_PREVIEW_REQUIRED")
    observed = _daily_preview_context(preview, config)
    approved_config = dict(
        config,
        APPROVED_COMMIT_CHANGE_ENVELOPE=copy.deepcopy(observed["changes"]),
        APPROVED_COMMIT_RETIREMENT_COUNTS=copy.deepcopy(observed["retirement_counts"]),
    )
    if observed.get("source_property_spec") is not None:
        approved_config.update(
            APPROVED_SOURCE_PROPERTY_LIFECYCLE_VERSION=_OSCAL_DAILY_LIFECYCLE_VERSION,
            APPROVED_SOURCE_PROPERTY_LIFECYCLE_CONTRACT_DIGEST=observed["source_property_lifecycle_contract_digest"],
            APPROVED_SOURCE_PROPERTY_RETIREMENT_DIGEST=observed["source_property_retirement_digest"],
            APPROVED_SOURCE_PROPERTY_DELTA_DIGEST=observed["source_property_delta_digest"],
            APPROVED_SOURCE_PROPERTY_PROCEDURE_NAMESPACE=observed["source_property_procedure_namespace"],
        )
    _load_require_approved_commit_envelope(observed, approved_config)
    return approved_config



def _daily_namespace_snapshot(context, lookups):
    """Resolve only authenticated field metadata, never source business records."""
    probe = dict(context, lookups=lookups)
    bindings = _owner_procedure_guid_bindings(probe)
    source = bindings.get("catalog.metadata.props[]")
    if source is None:
        raise ValueError("DAILY_WRITE_POLICY_SOURCE_NAMESPACE_REQUIRED")
    return {"binding_sha256": _daily_policy_hash(bindings),
            "namespace": source["namespace"]}


def _daily_namespace_recheck(graph, source_inputs):
    context = graph["context"]
    expected = graph.get("procedure_namespace_snapshot")
    if expected is None:
        raise ValueError("DAILY_WRITE_POLICY_NAMESPACE_SNAPSHOT_REQUIRED")
    actual = _daily_namespace_snapshot(context, source_inputs["source-two-source"].get("lookups", {}))
    if (actual != expected
            or context["config"].get("SOURCE_PROPERTY_PROCEDURE_NAMESPACE") != expected["namespace"]
            or _daily_policy_hash(context.get("_owner_procedure_bindings")) != expected["binding_sha256"]):
        raise ValueError("DAILY_WRITE_POLICY_NAMESPACE_CHANGED_DURING_RUN")
    return True


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
            source_input = source_inputs.get(active[0], {})
            selected_records = source_input.get("selection", {}).get("SELECTED_ROWS")
            if (source_input.get("source_df") is None or type(selected_records) is not int
                    or selected_records <= 0):
                raise ValueError("DAILY_WRITE_POLICY_SOURCE_TRANSPORT_CONTRACT_REQUIRED")
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
        if load_mode == "COMMIT" and daily_write_policy is None:
            raise ValueError("DAILY_WRITE_POLICY_REQUIRED_OR_INVALID")
        policy = (_daily_require_write_policy(source_inputs, mapping_contexts, daily_write_policy)
                  if daily_write_policy is not None else None)
        if policy is not None:
            report["daily_write_policy"] = policy
        for active, original in routes.items():
            context = copy.deepcopy(original)
            context["config"] = _daily_effective_lifecycle_config(context["config"], active)
            source = source_inputs[active[0]]
            context["lookups"] = source.get("lookups", {})
            expected = source.get("selection", {}).get("SELECTED_ROWS")
            if expected is not None:
                context["config"]["EXPECTED_SOURCE_RECORDS"] = expected
            namespace_snapshot = None
            if active == ("source-two-source", "CATALOG"):
                namespace_snapshot = _daily_namespace_snapshot(context, context["lookups"])
                previous_namespace = context["config"].get("SOURCE_PROPERTY_PROCEDURE_NAMESPACE")
                if previous_namespace is not None and previous_namespace != namespace_snapshot["namespace"]:
                    raise ValueError("DAILY_WRITE_POLICY_PROCEDURE_NAMESPACE_MISMATCH")
                context["config"]["SOURCE_PROPERTY_PROCEDURE_NAMESPACE"] = namespace_snapshot["namespace"]
            nodes, edges, result = run_oscal_mapping(source["source_df"], None, None, context["config"], context)
            graphs[active] = {"nodes": nodes, "edges": edges, "context": context}
            if namespace_snapshot is not None:
                graphs[active]["procedure_namespace_snapshot"] = namespace_snapshot
                _daily_namespace_recheck(graphs[active], source_inputs)
            report["groups"].append({"source": active[0], "model": active[1], "load": result,
                                     "mapping_fingerprint": context["compiled_plan"]["mapping_fingerprint"],
                                     "lineage": {key: value for key, value in context["graph_report"].items()
                                                 if key.startswith("LINEAGE_")},
                                     "native_catalog": {key: value for key, value in context["graph_report"].items()
                                                        if key.startswith("NATIVE_CATALOG_")},
                                     "security_impact": {key: value for key, value in context["graph_report"].items()
                                                         if key.startswith("SECURITY_IMPACT_")}})
        if load_mode == "COMMIT":
            _daily_namespace_recheck(graphs[("source-two-source", "CATALOG")], source_inputs)
            if any(graph["context"]["config"].get("LINEAGE_GAP_COUNT", 0) for graph in graphs.values()):
                raise ValueError("LINEAGE_COVERAGE_GAPS: review the graph lineage report before COMMIT")
            if policy is not None:
                # The pinned standing policy approves only these same invocation graphs.
                # It never reuses a previous run or expands the finite property boundary.
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
                    _daily_preview_context(preview, graph["context"]["config"]),
                    graph["context"]["config"],
                )
            for group in report["groups"]:
                active = (group["source"], group["model"])
                graph = graphs[active]
                _daily_namespace_recheck(graphs[("source-two-source", "CATALOG")], source_inputs)
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
