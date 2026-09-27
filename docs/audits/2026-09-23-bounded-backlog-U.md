# Bounded U: repeated provider cancellation generations

Parent: `b937ac3a10ca4d33aa4a1c6f3aef7cb03941e1b4` (S-T).

The registered headElevateCancelSeq reset medicAnimToken to -1. Each later start therefore reused 0, allowing a still-pending controller from an earlier cancel/restart cycle to match a new sequence. Cancellation now advances the existing counter instead of resetting it. Its delayed AUTO stance release captures and checks that cancellation generation, including when a newer sequence has already finished or been cancelled before delivery.

Only headElevateCancelSeq changes runtime. No new counter, state key, timer, PFH, network operation, animation, delay or patient/gear rule is added. The exact unarmed crouch, 0.25-second release, direct-pressure pause cleanup, duplicate-cancel no-op, and provider consciousness/locality/vehicle guards remain. The patient is not excluded because they are dead. No original H-index entry is closed by U.

Twenty-two full-source execution cases reproduce 20 failures and two passing controls on S-T. All 22 pass with the correction; the 80-test U selection includes the existing provider choreography, unconsciousness and weapon-preflight tests. Pending CBA handles are distinct fixtures. Tests cover both modes, four old-controller stages, repeated cancellation, negative/positive starting counters, delayed releases after another completion or cancellation, intact patient placement, and preserved current cleanup.

This does not certify live CBA scheduling, input, animation, multiplayer ownership migration, counter precision exhaustion, full-heal resets or calls to the unregistered legacy headElevCancelSeq file. It prevents generation reuse through the reviewed registered cancel path, not arbitrary external resets or all cross-controller races. Movement/menu cancellation remains open. No live Arma or stable-release approval.
