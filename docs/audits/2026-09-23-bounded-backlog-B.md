# Bounded continuation B: explicit supine Flip-cancel contract

Parent: `be99fd38dc90c575d656cc0b5937e15f73b059a5`.

The root phase-150 script required the obsolete one-argument patientRollCancel call. Runtime already requests `[patient, "front"]` to preserve the required supine exit. Only that assertion changes; every other assertion is retained. Batch A's full-Unload execution cases verify the actual anterior-up request during active Flip and the ordinary no-Flip controls. No runtime change in this batch.

The script now executes successfully. Entire root-tools probe before: {"passed": 137, "failed": 0, "error": 47, "skipped": 0}. After: {"passed": 137, "failed": 0, "error": 46, "skipped": 0}. Only the phase-150 collection error disappears. All other comparable root outcomes remain unchanged; both commands still return 1. Remaining root errors are open, not waived.

The root script's preservation digest is explicitly updated. Only the two reviewed snapshot cases, for this root script and Batch A's runtime, normalize their digest-valued parameter label for identity comparison; the complete original JUnit labels remain in evidence. Every other protected digest remains untouched. No new skip or xfail is introduced.

The separate historical addon-suite aggregate and original source-contract ledger are unchanged in this bounded pass. No Arma client, dedicated server or release package was run or approved.
