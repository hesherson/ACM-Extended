# B278 chest procedure cancellation through the medical menu

## Confirmed current gap

The reported B201 sequence was: choose Apply Chest Seal, press the medical-menu
key before the minigame loads, then find later attempts opening briefly and
closing immediately. Existing B263 protections already retire both the stock ACE
medical-menu PFH and ACME's renderer before closing the source menu. They also
bound patient-owner readiness and retain canceled-token tombstones.

A remaining gap was reproduced against the unmodified B277 entry controller in
SQF-VM: a fresh medical menu opened during preparation did not cancel that
preparation. The pending session either remained latched before readiness or
opened the chest panel over the newly requested menu once readiness arrived.
This confirms a current cancellation gap, not the complete cause of the older
reported incident.

ACE's supplied source binds the medical menu to H by default. Keydown requests
the menu; keyup can close it after the configured opening delay. The fix follows
the concrete medical display and ACME renderer generation, so it also works for
rebound keys and for a medical menu opened and closed between preparation ticks.

## Changes

- Chest preparation captures its original medical display and renderer epoch.
  A newer epoch or display retires the pending chest session before readiness can
  open a panel. The new medical menu is preserved.
- The final readiness callback rechecks those identities before transferring
  provider presentation into the workspace.
- `minigameOpen` accepts an optional guard and explicit guard arguments. Existing
  callers default to the original behavior. Both initial opening and the deferred
  native `createDisplay` callback evaluate the guard before changing UI state.
- The chest guard captures the session token, session serial, patient, provider,
  patient kit epoch, patient owner, provider locality epoch and source medical
  renderer epoch. A canceled or replaced episode cannot create a late panel.
- Existing close logic removes the exact pending PFH and input handlers, clears
  the preparation banner and dispatches the original session token's End to the
  patient owner. Existing patient-owner tombstones reject a delayed Begin after
  cancellation, while a fresh token remains eligible to start.

No new registered helper or network event is required. The production changes
are limited to `fn_chestSealOpen.sqf` and `fn_minigameOpen.sqf`.

## Validation

`test_b278_chest_menu_cancel.py` adds **22 executable SQF-VM cases** covering
medical-menu reopen before readiness, readiness on the cancellation frame,
open-and-close between sparse ticks, successful retry, stale entry callbacks and
watchdogs, owner End arriving before Begin, deferred display opening after
cancel/retry or identity changes, valid queued opening and default callers.

The final affected entry/modal group passed **67 cases**, with no failures or
skips. A broader chest entry, preparation, exit, workspace and modal group passed
**212 cases** immediately before the final patient-owner/provider-locality guard
extension; that final extension and four added invalidation cases are included
in the 67-case result. Scoped `git diff --check` passed.

Native display creation, physical animation and transport delivery are explicit
test boundaries. These results do not substitute for Arma dedicated-server
acceptance.

## Supplied log evidence

The attachment `Arma3_x64_2026-10-12_02-42-21 (1).rpt` contains 128,604 lines.
At line 183 it reports:

> Skipped loading of addon 'puo_acm_ifak' as required addon 'acm_core' is not present

Its only three case-insensitive ACM matches are that diagnostic and two
`puo_acm_*` testing PBO paths. There are no ACME/chest-seal diagnostic markers or
chest procedure SQF file locations. The 5,882 explicit SQF error-location lines
refer to CBA diagnostic `fnc_watchUpdate.sqf`, alongside repeated malformed debug
expressions. The supplied 69-mod preset has no Advanced Combat Medical entry.

This attachment cannot diagnose the B201 chest incident. It does not establish
the mod environment of the user's actual reproduction, and it provides no
evidence that another mod caused the chest cancellation failure.

## Native acceptance

On a dedicated server with matching current client/server packages, apply a
chest seal and press the configured medical-menu key during preparation. Check
both a short tap and a held press/release. Retry the chest procedure afterward;
the retry should open and remain usable. Repeat with patient ownership on the
server and on another client, and confirm carrier restoration and other medics'
existing chest sessions remain intact. The optional experimental display mode
also needs a cancel/retry check across its deferred opening frame.
