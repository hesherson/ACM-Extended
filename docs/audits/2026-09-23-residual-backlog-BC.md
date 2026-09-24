# Residual backlog BC: superseded head-position and surgical-airway test contracts

Parent checkpoint: `586271f324d74cace5f8d845065ee6e4499f1774` (validated BA-BB).

BC removes four false failures from the post-ledger residual suite without changing runtime SQF, config, networking, treatment logic or assets.

- B88 no longer asserts its retired asymmetric provider lift (`DraggerBasenon` / standing transition). B89 superseded that implementation with the shared exact-once Putdown sequence for elevate and lower. B88 now protects the current supersession contract, including the final crouch and release back to `AUTO`.
- B88 and B89 no longer pin historical `1.2.0-r0` / `B88` / `B89` literals. They use the repository's current release-identity validator.
- The transient reconciler no longer claims ownership of surgical-airway dialog lifetime. The live ACM continuous-action controller acquires `SurgicalAirway_InProgress` only from On Start and clears it from On Cancel.
- Retired `SurgicalAirway_InProgress_Session` metadata is explicitly absent. Internal cric UI clicks are not interpreted as treatment-lifetime changes.
- The surgical-airway start assertion now matches the current continuous-action payload `[_medic, _patient, "head"]`.

This batch is intentionally test/audit-only. A passing result here means the residual suite is measuring the shipped controller contract rather than older intermediate implementations.
