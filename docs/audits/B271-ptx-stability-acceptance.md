# B271 — Durable pneumothorax stability

Candidate **1.2.4.1 / B271**, protocol **1**, based on B270 `bccf824474292b5f64107a85e68fe9e75226876c`.

## Result

Previously, a finger thoracostomy relieved trapped air while retaining an internal leak. Sealing the surgical tract removed its drainage capacity, allowing that same leak to rebuild PTX until slow natural healing completed. B271 adds a deliberate gameplay recovery path: definitive drainage can settle the current injury's internal leak permanently after a continuous controlled observation interval. This is a simulation policy, not a clinical treatment recommendation.

The existing **Pneumothorax stability interval** setting controls this interval, default **60 seconds**. The patient must have a patent finger tract or chest tube; all recorded communicating traumatic wounds, including undiscovered exit wounds, must be covered; tension must be relieved; internal air must be at most 1 and pressure at most 0.1; air must not be increasing and drainage must cover incoming air. Losing any controlled condition resets the observation timer. Completing the interval sets internal leak to zero. Residual collapse is retained rather than claiming immediate full lung recovery.

Surgical sealing and native incision closure require the settled leak and the full controlled observation interval. Early surgical sealing is rejected before the minigame reserves a chest seal. The patient owner rechecks readiness immediately before closure, so a concurrent injury or another provider's closure can reject and refund the original reservation safely. Ordinary traumatic-wound sealing remains available during observation and does not prematurely close an unstable surgical drain. Native closure completion is logged only after the owner accepts it.

NCD and ordinary wound seals retain natural internal-leak healing; they do not receive the definitive-drain acceleration. Existing burp, drainage and NCD residual-floor policy remain. New penetrating injury or an external native severity increase resets observation and may create another leak. Closing and reopening the UI, an equal native severity projection, or repeated sealing cannot regenerate an already settled leak by themselves.

## State and multiplayer boundaries

The nine-number version-1 PTX state and network protocol remain unchanged. A persisted observation revision marks timers earned under the stricter B271 criteria. Adoption of an older episode discards its old quiet-air credit once, preserving air, leak and injury identity. Old snapshots cannot borrow a marker from a newer patient; current snapshots preserve qualified observation. Full heal clears the marker through the existing field registry.

Seal placement reserves supply on the original request machine and sends one identified owner transaction without optimistic tract writes. Accepted and rejected seal results are cached for 120 seconds of inactivity. The request machine queries the same transaction every 16 seconds while its exact receipt remains reserved; known queries renew the result lease. Duplicate replies settle the receipt once. Unknown stale requests receive no guessed terminal reply, because missing evidence cannot prove whether the seal was used. Widening retains its existing single reconciliation query and transaction policy.

## Native acceptance

Use matching complete B271 packages on the dedicated server, two clients and any HC, with the separate original ACM disabled.

1. Create PTX, perform finger thoracostomy, cover every communicating wound and relieve tension. Try to seal early: the incision stays patent and no minigame seal is consumed. Maintain drainage for the configured controlled interval, seal or close, then observe for at least ten minutes. The same injury must not rebuild its internal leak or tension.
2. Repeat with a chest tube, remove it after observation, and close the incision. Check contralateral drainage and ordinary wound seals remain independent. Regress NCD and burp behavior without granting the accelerated recovery to NCD alone.
3. Interrupt observation with an uncovered exit wound, worsening PTX, tension or new injury. Confirm the full interval must be earned again. After successful closure, inflict a genuinely new injury and confirm it can cause new PTX.
4. Race two providers sealing the same tract; inject new injury between provider preflight and owner acceptance. Transfer patient locality during requests and delay acknowledgements. One accepted closure consumes one seal; rejected and duplicate transactions settle once without changing a successor tract.
5. Switch to another patient while a reply is pending, reset/full-heal the original patient, close/reopen the workspace, and load old and current snapshots. Verify pending inputs and old timer credit cannot block or prematurely close a new episode.
6. Regress healthy/dead mechanical aftercare, native ordinary chest seals, native incision closure logs, tension relief, residual collapse and positive-pressure delivery. Record exact build, settings, RPT and before/after patient dumps for any failure.

Automated SQF execution adapts native engine/UI/network operations explicitly. It does not establish native Arma, Windows deployment, live locality transfer or multiplayer acceptance. This remains a draft development candidate, with no main merge or public release.
