# Stable 1.2.4.1 B211 Direct Pressure input restoration

Base: B210, `ca3b2b8e41f8a03377063990c3860e6bc78ee2af`.
Public version remains `1.2.4.1`; runtime and all package components identify as `B211`.

## Report and cause

Movement released Direct Pressure instead of allowing repositioning and returning to the hold. The shared tick explicitly interpreted movement, turning and evasive input as a complete cancellation. The pose controller already had a movement-yield path, but this earlier exit prevented it from running.

The display handler accepted middle-click only, while the supplied ACE mouse-hint implementation interprets the existing hint as right-click. The handler was attached only to mission display 46, leaving the open medical menu without the same input route.

## Correction

- Keep the exact pressure episode, worker and patient claim during repositioning within the existing reach limits. Movement yields the visual pose; the first stationary, patient-facing tick resumes it with no added idle delay.
- Retain provider incapacitation, patient/vehicle separation, distance and lost-claim cleanup. Existing treatment and CPR/BVM yield/resume behavior remains.
- Accept right-click cancellation, with middle-click retained for compatibility. Keep the existing right-click hint and explicit Stop Direct Pressure menu action.
- Install the same handler on each medical-menu display when it opens, with display-local duplicate protection. Other minigame displays keep their own input handling.
- Preserve the provider's competing intervention controls. Recheck ownership at deferred cancellation and match the original provider, locality generation, pose token and clinical claim identity before releasing pressure.
- Prevent an older delayed movement-exit callback from breaking an already resumed hold.

## Validation

All 1,753 distinct required cases passed: 75 ownership, 897 existing network, 689 behavioral and 92 B211 input cases. The first network run included the initial 55 B211 cases (952 passes); the finalized 92-case module was then rerun in full, replacing that initial subset in the distinct count. Its B210 old-source comparison reports 68 failures and 24 passes.

HEMTT check and Linux `release --no-bin --no-archive` pass. All 14 PBO signatures and B211 component stamps verify; the strict native-state ownership audit reports zero violations. The additional related-contract run had 27 passes and the two inherited failures described below. Exact totals and limitations are recorded in `2026-09-30-b211-results.json`.
The regression harness executes production claim, tick, pose, mouse-handler and stop logic while explicitly simulating native objects, input, UI registration, animation and transport. It cannot certify actual Arma rendering or event delivery.

The broader historical suite was not rerun for this targeted input patch. The related contract run retained two failures already present in the B210 full report: an obsolete recovery-sweep interval expectation and an obsolete public-version expectation in `test_player_grievance_fixes_20260926.py`. Their assertions and production targets are unchanged by B211. The old MMB-only test retains its identity but now checks the user's requested RMB/MMB contract.

## Live acceptance

1. Test torso, head, limb and self pressure. Press each movement direction, turn and briefly reposition within reach. Pressure must remain active; other-patient hold animation returns when stationary and facing the patient.
2. Right-click with the medical menu closed, open and reopened. Pressure must release its claim and stop once; another medic can immediately take the site. Middle-click and the explicit Stop action remain available.
3. Start CPR/BVM while pressure is suspended. Their pause/swap buttons must retain their meaning. A queued old cancellation must not cancel a replacement hold or new provider.
4. Walk outside reach or separate vehicles; pressure must still stop. Repeat on dedicated-server/client-owned patients and during patient/provider ownership changes.

Import the B211 bundle into the B210 checkout and run `tools/Deploy-ACME-B211.ps1`. A process-scoped `powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File` invocation supports the user's local script-execution policy without changing permanent settings. Restart and use the complete same build on participating machines.
