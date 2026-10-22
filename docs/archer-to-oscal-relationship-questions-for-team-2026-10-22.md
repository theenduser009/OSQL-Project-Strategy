# Archer → OSCAL: Questions for the Team

**Date:** October 22, 2026  
**Purpose:** Confirm the business meaning, direction, and ownership of Archer relationships before mapping them into OSCAL.  
**Scope:** Authoritative Sources, Topics, Sections, Sub-Sections, Control Standards, Control Procedures, and Policy Levels 1–3.

## Opening question — copy and ask in the meeting

> I'm validating our Archer-to-OSCAL mapping, particularly the connections between Authoritative Sources, Control Standards, Control Procedures, and Policies.
>
> We have already checked that the technical references resolve in the source data. Now I want to confirm that we interpret their business meaning and ownership correctly.
>
> Could we walk through **one real example in Archer**: Authoritative Source → Topic → Section → Sub-Section → Control Standard → Control Procedure? Then could we trace how Policy Level 1 → Policy Level 2 → Policy Level 3 connects to that same Control Standard?
>
> I want to understand which relationships are directly assigned in Archer, which are calculated or rolled up, and which appear only as reverse related-record references. The goal is to represent the relationships correctly in OSCAL rather than attach a Procedure to the wrong Control.

## Follow-up questions

### 1. Section and Sub-Section ownership

- Can a Section link directly to a Control Standard even if there is no Sub-Section?
- Can a Sub-Section and its parent Section both link to the same Control Standard?
- Can the same Control Standard be linked to multiple Sections or Sub-Sections?
- When that happens, which relationship is direct and which—if any—is inherited or calculated?

### 2. Control Procedures: direct versus derived relationships

- Are the Control Procedures displayed on Source, Topic, Section, and Sub-Section records **directly selected there**, or are some automatically gathered from lower levels or from the referenced Control Standards?
- If a Source/Topic/Section references a Procedure but none of its directly referenced Standards do, is that an intentional direct business relationship or a calculated/historical rollup?
- Conversely, should every Procedure referenced by a Control Standard appear on the owning Section or Sub-Section?
- Which Archer field should be treated as the authoritative source for each type of relationship?

### 3. Cross-Reference (CR) versus Related Record (RR)

- Which Archer field is the **original Cross-Reference**, and which field is its **Related Record** counterpart?
- Does Archer maintain the reverse view automatically, or can someone independently edit both sides?
- Can two separate CR/RR configurations connect the same two modules for different business purposes?
- How do we tell a genuine second relationship from a reverse display of an existing one?

### 4. Policy hierarchy

- Is Policy Level 1 → Level 2 → Level 3 a strict parent/child hierarchy?
- Does Policy Level 3 reference Control Standards directly?
- Can a Control Standard belong to multiple Policy Level 3 records?
- Are links from higher policy levels directly stored, or derived from Level 3?

### 5. Snowflake extraction / Matillion transformation

- Are these relationship arrays copied directly from Archer, including both CR and RR fields?
- Does the extraction or Matillion process calculate, flatten, aggregate, or expand any relationships?
- Are there source-level rules, filters, or historical fields that change which relationships appear in the CURATED_JSON?
- What field/level metadata should we use to validate the original owning side of a relationship?

## Separate question for the OSCAL architect / mapping owner

> When an Archer relationship doesn't have a suitable native OSCAL element, does the team have an **approved extension-property namespace URI**? Should Procedure references be represented as source identifiers in namespaced `props`, or as `links` to actual Procedure resources?
>
> For new custom properties, are we agreed that `prop.name` should use the original Archer field's stable `FIELD_GUID`? How should multi-valued Procedure IDs be encoded, and how should group-property inheritance be handled so a reference on a Topic/Section/Sub-Section does not incorrectly apply to every Control within that group?

## Desired outcome from the walkthrough

Capture **one concrete example** with its original record ownership, the CR and RR field definitions, whether each link is direct or derived, and the expected relationship path. Use that example to agree on the OSCAL model/path and extension policy before activating new mappings.

*Public-safe meeting preparation only. No internal field IDs, source business records, validation counts, credentials, or customer-specific SQL are included. This document is not an approved mapping or deployed implementation.*
