# Stable 1.2.4.1 B209 runtime follow-up

Base: `1bf8e5d7856060f037512e77bc6a38ae634d0b5f` (B208).
Public version remains `1.2.4.1`; runtime/package identity is `B209 | NA8-B209-1.2.4.1-stable`.

## Reproduced problems and corrections

- **Esketamine activity log:** the intranasal action emitted `medicationLocal` directly, bypassing the native medication wrapper's activity and triage entries. The action now uses that wrapper with the actual atomizer item and explicit Esketamine effect class. A 50 mg atomizer remains one product unit; neither dose nor effect event count increases. Four execution cases failed before this change and pass afterward, covering both supply donors and repeated administrations.
- **Native syringe preparation:** repairing the shared test fixture exposed a real older defect behind three previously blocked tests. Preparation consumed the raw floating-point draw but stored a different hundredth-of-a-milliliter quantity in the physical magazine. The Narc Box retained the raw draw, so later push reservation could search for an ammo amount the magazine did not contain. A tiny draw could also consume supplies while producing a zero-ammo syringe. Preparation now normalizes the accepted volume once, uses it consistently for the vial, physical syringe and stored row, and rejects draws that round to zero. Failed container reservation preserves the source volume.
- **Semi-Fowler into CPR:** native CPR entry lacked lowering even though supported Semi-Fowler deliberately survives BVM. CPR now reserves the episode, yields its existing Direct Pressure pose, and waits for patient-owner confirmation before enabling compressions. The owner acknowledges accepted lowering as pending and confirms readiness after the guarded completion callback. Retries are bounded; cancellation, replacement and ownership checks prevent an old request from authorizing a new episode. Middle-mouse CPR/BVM handoff preserves chest-access custody before releasing the outgoing controller.
- **Deferred head placement:** pending normalization could restart after cancellation, a newer placement or ownership changes. Local start generations, clinical reset and Local-event invalidation fence the continuations. Manual placement also rechecks provider life, consciousness and range before changing patient state; automatic transport restoration retains its providerless path.
- **Vehicle treatment:** the treatment bridge incorrectly removed ACE's `isNotInside` exception for a shared vehicle. ACE permits another occupant through that general condition but excludes self, so the bridge could reject otherwise valid seated self-treatment. The native exception is retained. CPR/BVM session distance checks also respect shared-vehicle treatment. Treatment-specific equipment, clinical and physical-position conditions remain active.
- **Direct Pressure provider migration:** the old machine's pressure and held-animation callbacks could survive a provider transfer. Captured claim and locality generations retire old workers, release only their original patient reservation, and request matching current-owner cleanup. A late cleanup must not cancel a newer pressure episode or use another machine's handler IDs. The generic held-animation helper retains remote patient choreography by default; only provider-owned pressure opts into local-only execution.
- **Medication store and worker ownership:** live Hardcore plunger/refund writes use the owner-guarded store writer with publication disabled; normal final settlement publishes once. This avoids broadcasting 20 Hz updates. Captured session, worker ID and locality generation prevent an obsolete callback from affecting a replacement push. Lost/deleted/replaced-provider workers retire locally while preserving unsettled job, row and escrow evidence. They do not deliver medication, invent refunds or write remote inventory. Retired records are bounded without eviction. A fresh-kit reset retires that provider's active worker before replacing its inventory and clearing the corresponding local record; delayed Hardcore acknowledgements cannot restore the old push into a new kit.

## Test repair and retained behavior

The B208 audit classified its 836 nonpassing records as 622 harness/VM boundary problems, 197 superseded checks and 17 behavioral or architectural records needing review. These were first-failure classifications, not certification of assertions that never ran.

The native preparation defect demonstrates that limitation: three tests previously stopped at a missing helper, and fixture repair let their actual conservation assertions fail. Those failures were investigated and the runtime corrected. Remaining fixture failures do not establish that their later, unexecuted assertions would pass.

Shared fixtures now load registered production helpers, initialize current active-patient/controller state and adapt explicitly unsupported engine primitives. Original behavioral assertions are retained. The HPMK source check targets its actual visual worker while preserving the prohibition on recurring whole-world scans. The release-identity validator rejects malformed batch names. The Narc Box ownership contract now executes as a named test, retaining its original assertions, rather than disappearing silently when its previous collection failure is resolved.

The old animation signature assertion now executes the omitted-option path and checks that remote-patient choreography retains priority 1. A generated head-stop mutation-test ID is explicitly preserved. The chest-flip test now reflects its current completion policy: a cancelled provider pose does not keep the button locked after the patient interval completes. Four execution cases retain the lock before that interval, verify one-time release afterward and protect a newer provider pose. No chest-flip runtime change was needed.

Repaired behavioral modules join a required all-pass CI gate. The historical full-suite comparison still exposes remaining failures and rejects missing, skipped or newly failing cases; historical baseline equality is not treated as a green suite.

The audit's remaining direct native-state writes were reviewed, not mechanically rewritten to satisfy old source greps. Clot/progress reconciliation already checks patient locality. The physical-dressing setting remains a deliberate per-machine invariant; removing it would reintroduce spontaneous bandage reopening. Client visual timestamps and renderer retirement remain bookkeeping. Direct Pressure remains promoted in the medical menu alongside the newer carrier action. No new damage-state API or recurring scan was added solely to silence these architectural checks.

## Validation and limits

- **1,601 required checks pass:** 75 ownership, 837 network execution and 689 repaired behavioral cases. The strict native-state ownership audit reports zero violations in its four audited domains.
- **Build/package:** HEMTT 1.22.0 `check` and `release --no-bin --no-archive` pass. All 14 PBO signatures, all 14 B209/protocol/component config stamps and the signing key verify.
- **Complete final run:** 6,110 passed, 332 failed, 45 errors and 29 skipped, counted by JUnit testcase identity. The source remained unchanged throughout the final run; no result reconciliation was needed. Pytest's console reports one additional pass and failure because one temperature-assessment parent completes with two failing unittest subtests; these are not missing cases.
- **Regression comparisons:** B208 and the original B204/main baseline both pass, with no newly failing, skipped or missing test occurrences. Against B208, 177 new cases pass, 458 existing cases improve and one collection error resolves into an executed passing test.
- **The full suite is not green:** 377 inherited failure/error records remain. Their current first-failure review comprises 197 obsolete/source checks, 176 fixture or unsupported-engine barriers and four architectural-contract records. This classification does not certify unexecuted assertions behind those barriers. Repairing the earlier fixtures exposed the native syringe defect described above; inherited status alone was not accepted as proof of correctness.

The new syringe tests produce seven behavioral failures against the immutable B208 native functions and pass all nine cases with the correction. The three existing B156 preparation-volume assertions also pass without changing their expectations. Esketamine's four previously failing execution cases pass.

See [machine-readable validation summary](2026-09-30-b209-results.json).

Arma UI/rendering, native animation execution, real network delivery and Windows asset binarization are not executed by SQFVM or the Linux package check. Dedicated-server/two-client/headless-client acceptance and a representative-load soak remain necessary.

**Hardcore push ownership transfer remains a limitation:** the plunger job is client-local. Retiring the old worker and retaining evidence does not transfer its unsettled transaction to the new owner. Automatic continuation/refund after a mid-push provider transfer is not claimed. On the original machine an affected provider needs a fresh kit before another Hardcore push; unrelated providers can continue unless the bounded retirement capacity is full.

## Live acceptance

Use the same complete B209 package on the server, clients and headless clients, then restart them. Check the B209 debug marker on each machine.

1. Administer Esketamine from medic and patient supplies; verify one activity/triage entry and one effect per atomizer.
2. Draw fractional syringe volumes and confirm the vial debit, physical syringe and Narc Box agree to 0.01 mL. A draw that rounds to zero must preserve the barrel and medication; a prepared physical syringe must remain selectable for a Hardcore push.
3. Start CPR from supported and manually held Semi-Fowler; exercise BVM/CPR swaps, cancellation during lowering, delayed owner replies and another provider competing for the same casualty. Confirm carrier continuity and pressure resumption.
4. Cancel or replace pending head placement during a roll, after full heal and across patient ownership changes. Repeat after provider death, unconsciousness and leaving range.
5. Test permitted self/passenger interventions and CPR/BVM in a large vehicle with distant seats; check that the existing physical-position restrictions still apply.
6. Transfer a pressure provider between machines, including away/back transitions and a new pressure episode before the old cleanup arrives. Confirm no old pose, clot request or reservation clears the successor.
7. Exercise ordinary Hardcore push completion/rejection/stop, then the documented provider-transfer containment path. Confirm no background worker persists and no automatic uncertain refund is created.

Deploy from the updated branch with `tools/Deploy-ACME-B209.ps1`.
