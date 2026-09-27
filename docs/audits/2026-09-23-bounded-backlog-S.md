# Bounded S: provider consciousness during head-position theatre

Parent: `fce7d83f742b51b037a7d252bda3d132950580e8` (Q-R).

The active provider controller checked life/locality/vehicle state but not ACE unconsciousness. An unconscious provider could start or continue the Putdown sequence. The registered cancel path and the post-finish/post-cancel stance release also lacked that exclusion.

Only headElevMedicSeq and headElevateCancelSeq change runtime. Reject an already unconscious provider before dispatch/preflight; retire an interrupted current controller without a new weapon, crouch or delayed stance request; suppress deferred stance changes if consciousness is lost before delivery. Existing ownership-token checks and DP pause cleanup remain. This is a provider condition, not a dead-patient exclusion. No casualty state, medical treatment gate, animation name/timing, equipment algorithm, new timer or network operation is added.

24 full-source execution cases: unchanged Q-R has 18 failures and 6 passing controls; candidate all pass. Coverage includes both modes, four controller stages, remote/local rejected entry, explicit cancel, loss of consciousness before delayed release, dead-casualty/conscious-provider controls and newer-token preservation. Existing sequence and weapon-preflight modules are retained.

The engine boundaries record requests; no real animation, input, unconsciousness transition, scheduling, PhysX or networking is simulated. This does not establish post-wake stance recovery, automatic menu/movement cancellation, token-reuse handling or general cross-controller ownership. The unregistered legacy headElevCancelSeq file is unchanged; this patch targets the registered controller/cancel path. No H-index entry is closed by this runtime correction. No stable-release approval.
