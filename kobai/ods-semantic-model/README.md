# OSCAL ODS semantic model for Kobai

**Release 1.1.0 — October 22, 2026. ODS schema and model definitions only.**

This folder is a vendor-facing specification for modeling OSCAL objects stored in an ODS as DIM elements and FACT dependencies. It contains table names, column definitions, logical concepts, selected attributes, and relationship-resolution rules. **It contains no company records, samples, screenshots, populated identifiers, credentials, or upstream object/mapping details.**

## Start here

- [YAML model specification](oscal_ods_semantic_model.yaml)
- [Equivalent JSON specification](oscal_ods_semantic_model.json)
- [ODS table and column dictionary](ODS_TABLES.md)
- [Local validation report](VALIDATION.json)

YAML and JSON describe the same model. Use whichever format suits your implementation. They are a vendor-neutral specification, **not a verified native Kobai import**, and not an OSCAL instance document. Translate them into the modeling and mapping interface supported by the deployment.

Kobai describes its knowledge model in terms of domains, concepts, properties, and relationships. This package supplies those design inputs together with ODS table bindings; it does not create an active connection or authorize access to records. See [Kobai's knowledge-model terminology](https://help.kobai.io/knowledge-model-introduction).

## The five model modules

| Module | Meaning in the semantic model | Important distinction |
|---|---|---|
| System Security Plan (SSP) | A system's documented characteristics, components, and control implementation. | The SSP document and a real-world enterprise system are not automatically the same entity. |
| Assessment Plan | The scope and planned activities of an assessment. | A reference to an SSP must identify the actual document; co-occurrence is not a reference. |
| Assessment Results | Assessment-result occurrences and their observations, findings, and risks. | A score, count, or named property is not automatically a finding or an assessed-control relationship. |
| Plan of Action and Milestones (POA&M) | Remediation tracking with relevant risk and observation references. | A retained item reference may lack the complete item details. |
| Catalog | Control definitions organized into groups and subgroups. | A catalog control definition is different from a system-specific implemented requirement. |

These descriptions and the selected conceptual paths are grounded in [OSCAL 1.2.3](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/). They do not claim that every object in the full OSCAL standard exists in the ODS or that every attribute is populated. Profile and Component Definition are explained as optional context only; this publication supplies no physical table pair for them.

## What DIM and FACT mean here

A DIM row is an identified **element occurrence**, not an entire model definition and not necessarily a globally unique real-world asset. One DIM table can hold a document root, metadata, characteristics, components, and separate property elements. `ELEMENT_TYPE` helps classify a row, but owner path and model context are also needed.

The corresponding FACT table supplies parent and child references for physical `CONTAINS` relationships. Preserve the existing hash keys. Do not create new identities from titles, names, row positions, or assumed global control IDs.

For each model, resolve `FK_SOURCE_ELEMENT_HASH` against the parent's configured DIM primary key and `FK_TARGET_ELEMENT_HASH` against the child's. The **SSP primary-key names are exceptions** to the other models' naming pattern; use the supplied names exactly. UUID endpoint columns provide an additional consistency check, not a license to ignore scope.

The table and column declarations were checked against configuration and loader definitions. They are **not a fresh live Snowflake schema or row validation**. Database and schema qualification is left for internal configuration. The term ODS describes the integration boundary; it does not rename the physical schema.

## An attribute is not automatically another node

For system name, the design is:

**SSP → System Characteristics → system-name attribute**

The first connection is a parent-child relationship. `system-name` is a member of the characteristics element's `METADATA_JSON`, read as `METADATA_JSON:"system-name"::STRING`; it is not another DIM element. System Characteristics is a singleton object within the SSP, not a collection and not a separate OSCAL model.

`props[]` needs different handling. A property may be stored as a separate DIM child, or inline in another element's payload. The adapter must preserve the actual representation and the property's owner, namespace, and name. The public package deliberately omits company-specific property dictionaries and all property values.

## Three relationship categories

**Containment:** Resolve an actual `CONTAINS` FACT edge and verify the expected parent/child paths. For example, an SSP can contain System Implementation, which can contain Component occurrences.

**Derived relationships:** A semantic `SSP_DOCUMENTS_COMPONENT` relationship can summarize those two validated edges. It must retain its derivation and must not be described as a direct stored FACT edge.

**Reference and cross-model relationships:** Use explicit, scoped references. Examples in the design include Assessment Plan → SSP via `import-ssp.href`, Assessment Results → Assessment Plan via `import-ap.href`, and a responsible assignment → Party via `party-uuids`. An identifier comparison must resolve uniquely in the correct context. These relationships remain inactive until verified in ODS. Do not infer Observation → Control or POAM Item → Finding from counts, labels, or shared provenance alone.

Predicate names in this package are proposed semantic vocabulary, not claims that those labels already appear in `DEPENDENCY_TYPE`.

## Path resolution and schema-level lineage

The supplied DIM contract does not persist `ELEMENT_PATH`, `PARENT_NODE_PATH`, or instance keys as dedicated columns. Resolve paths through verified ownership and an internally approved ODS path definition. Repeated `groups` or `props` labels alone are insufficient. If a path is ambiguous, stop and resolve it internally; no access outside ODS is required or requested by this package.

Lineage here means the **design of traceability**: the ODS table, key columns, owner path, JSON member, relationship rule, and available technical audit/provenance column definitions. No lineage values, source identifiers, run identifiers, or upstream table identifiers are published. No separate lineage table is asserted or invented.

The FACT contract has no sequence column. Do not promise complete order-preserving OSCAL document reconstruction solely from this structure.

## What the implementation team should deliver

Create the five modules, their selected concepts and properties, and explicit relationship rules. Bind them to the named ODS DIM/FACT tables, using internal database/schema configuration. Keep concept availability and relationship activation separate from the conceptual design.

The authorized internal team must check actual schemas, owner paths, representation choices, approved property selection, endpoint uniqueness, and reference resolution before activation. Missing keys, explicit nulls, empty strings, zero, and false must not be silently equated. Empty or missing references must not generate invented edges.

No company records are needed to review these definitions. **This publication grants no record access, requests no sample upload or data export, and does not change any pipeline, table, or warehouse row.** Any later connection or record processing requires its own authorization. Validation against actual records stays inside the authorized environment.

## Release boundary

This ODS-only folder is the public handoff. Internal mapping/evidence packages are not part of it and must not be copied into this folder. Approval to publish these model definitions and table names is not approval to disclose data or upstream designs. Share the files in this folder, rather than treating unrelated repository files or history as part of the reviewed package.

## Public reference documentation

- [SSP reference](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/system-security-plan/json-reference/)
- [Assessment Plan reference](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/assessment-plan/json-reference/)
- [Assessment Results outline](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/assessment-results/json-outline/)
- [POA&M outline](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/plan-of-action-and-milestones/json-outline/)
- [Catalog outline](https://pages.nist.gov/OSCAL-Reference/models/v1.2.3/catalog/json-outline/)
