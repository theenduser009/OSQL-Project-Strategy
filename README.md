# OSCAL public copy-and-run workbench

**Current step — October 14, 2026: one guarded Source Two six-field Sub-Section DEV COMMIT.**

**WARNING: The Python cell linked below intentionally WRITES to Snowflake DEV DIM/FACT targets. It is NOT a read-only diagnostic.** Run once only, after reviewing your targets and pausing other Catalog writers. It must not be retried blindly after any failure or unknown transaction outcome.

## Two steps, no old mapper/QA reruns

**1. Install the matching revised Source Two Cell 6 loader** in your existing Snowflake DEV notebook, replacing the existing Cell 6 code, and **run that updated Cell 6 alone**:

[Updated Cell 6 with fixed D/F delta guard](https://github.com/theenduser009/Oscal-mapping-strategy/blob/work/source-two-sixfield-dev-commit-guard-2026-10-14/notebooks/staging/source-two-topic-only-2026-10-13/06_validation_and_guarded_loader.py)

This defines the loader; it does not execute the old Cell 7 or target DML. It adds an **opt-in** exact change envelope checked **before BEGIN TRANSACTION** and **again within the transaction before MERGE**. Existing target identity, graph ownership, baseline, rollback, orphan, audit, and post-COMMIT readback validation remain active.

**2. Copy/run only the current PUBLIC guarded COMMIT cell:**

[**Source Two — Six-field Guarded DEV COMMIT**](notebooks/source-two-subsection-sixfield-guarded-dev-commit.py)

Paste the entire script into **ONE new Python cell below your previously successful six-field RAW QA**, in the same Snowflake notebook session. Run it **once**, with the same Snowflake DEV role and approved target tables. It requires the existing `STANDARD_CELL_7` QA PASS and reuses the exact graph validated against 20,000 original Archer Sub-Sections. No old Cells 1–5, old Cell 7, Source One scripts, registry SQL, or raw reloading is required.

The script hard-limits this batch to:
- **DIM**: `INSERTS=0`, `UPDATES=20000`, `UNCHANGED=13679`
- **FACT**: `INSERTS=0`, `UPDATES=0`, `UNCHANGED=33531`
- **No retirement or deletion**; exact Source Two CATALOG DEV route only.

The revised loader refuses to write if the current target delta differs. It checks again inside its transaction. It automatically rolls back on a within-transaction mismatch before MERGE. It then verifies actual saved changes and reports `COMMITTED_AND_VERIFIED` and zero outstanding DIM/FACT inserts/updates.

**Expected success output:** `SOURCE_TWO_SIXFIELD_DEV_COMMIT_RESULT` containing `status: COMMITTED_AND_VERIFIED`, `expected_changes` matching the fixed envelope and `verification.DIM / FACT` with zero pending changes; plus `RESULT: SOURCE_TWO_SIXFIELD_DEV_COMMITTED_AND_READBACK_VERIFIED`.

**If any error appears: STOP, do not rerun the COMMIT cell.** Send only aggregate status/error (no business payload). The loader can report an unknown transaction outcome on transport failure; a blindly repeated attempt is prohibited.

## Release-state boundary

The six new mappings have passed a no-write PREVIEW and independent original Archer RAW value parity QA (20,000 children; field mismatches 0, direct prose differences 0). That QA **does not prove a physical COMMIT**; only the owner's new COMMIT + post-write readback can do so.

The four other staged fields (INFORMATION, SUBSECTION_CRITICALITY_VALUE and two Sub-Section timestamp fields) remain deferred. Policies/Control Standards are separate mapping work, not part of this commit.

The full 62-row mapping CSV and dated engineering decisions remain in the separate OSCAL source-of-truth repository. Do not put source payload values, sensitive metadata, or credentials in this PUBLIC workbench. The Source Two QA script was retired from public main after owner acceptance, but remains recoverable through Git history. The unrelated Change Control trace SQL remains untouched.
