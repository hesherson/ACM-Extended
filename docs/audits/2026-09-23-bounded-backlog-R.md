# Bounded R: current provider Putdown sequence and patient wrappers

Builds on Q from O-P. No runtime change in R.

H330, H342 and H352 retain their identities. They demanded retired DraggerBase/AnimDone provider choreography and raw patient state names. B89 intentionally uses the same unarmed crouch -> Putdown entry -> Putdown exit -> crouch sequence for Elevate and Lower Head. It adopts an already-running exit without replaying it, then releases temporary stance control. Connected patient wrappers retain BI grab/release inheritance verified by bounded N. No obsolete sequence is restored.

Nineteen new cases pass on unchanged provider code. They execute the complete controller with animation/clock fixtures or reject mutations with comment decoys. Coverage: both modes, exit adoption, no repeated requests while states stay visible, weapon-preflight grace, unseen-state timeouts, superseded PFHs, final crouch and invalid/newly-owned delayed stance release. The existing logical empty-weapon fallback is retained. No automatic weapon re-selection is introduced.

These fixtures do not certify movement/menu cancellation, physical RTM blending, actual scheduler order, patient rendering or multiplayer delivery. H343/H344 remain open. No runtime, configuration, asset or protected snapshot changes in R. No skip/xfail added. Index 106 to 103; all unreviewed test bodies and H entries unchanged.

## Complete-checkout validation

Focused: {'passed': 191}. Q on original runtime: {'failed': 16, 'passed': 4}; R on original runtime: {'passed': 19}. Full addon before: {'passed': 4134, 'failed': 135, 'skipped': 4}; after: {'passed': 4177, 'failed': 131, 'skipped': 4}. Exactly four retained historical identities pass and all 39 new cases pass. No new failure or missing prior identity. Both full addon commands still fail overall, with four unchanged skips and zero collection/setup errors. Root before: {'error': 46, 'passed': 137}; after: {'error': 46, 'passed': 137}, with identical normalized identities/outcomes. Only one reviewed digest-valued snapshot label is normalized; raw JUnit is retained. HEMTT check returns 0. Only headElevateStart changes runtime. All 4071 other existing tracked files retain SHA256. No live Arma or stable-release approval.
