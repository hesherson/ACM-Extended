# Stable 1.2.4.1 B206 dedicated-server action fixes

Base: `f87cacd71604aae1ec832dc22a48f7d41d9e9aac` (B205).
Runtime identity: `1.2.4.1 | B206 | NA6-B206-1.2.4.1-stable`.

## Evidence and cause

The supplied client RPT contains six `Cleared stale Direct Pressure claim request` messages. The provider watchdog emits this after a pending request exceeds four seconds without a matching acknowledgement. No Direct Pressure SQF exception or patient-side claim-repair message accompanies these failures. The screenshot identifies B201; the same transport defect remained in B205.

Direct Pressure populated its provider reply address with `owner _medic` on the medic's client. Bohemia's [owner documentation](https://community.bohemia.net/wiki/owner) specifies that this command returns zero outside the server; [multiplayer scripting guidance](https://community.bohemia.net/wiki/Locality_in_Multiplayer) identifies `clientOwner` as the current machine ID. A dedicated casualty owner rejected the zero provider ID, then sent its acknowledgement to that same invalid address. A player/HC casualty owner could accept the zero comparison but still fail to return the acknowledgement.

The IV/IO cache-shape entries are incidental initialization repairs: 119 across mission sessions, rather than a sustained Direct Pressure repair loop. The RPT also reports HPMK callback argument type errors and numeric facility/evacuation positions passed to `parseNumber`. Those errors are fixed here. The larger ACE icon-coordinate error flood has not been proven to have a single cause, and this patch does not claim to resolve unrelated modpack errors.

## Changes

- Direct Pressure originates claims with `clientOwner` and addresses replies through CBA's object-targeted event. Server-side owner checks remain authoritative; a nonserver local provider is checked against `clientOwner`. Remote player/HC casualty owners retain the episode/epoch guards without comparing a client ID against the unavailable remote `owner` result. Stop, timeout, delayed acknowledgement and reconciliation retain token-scoped cleanup.
- Hang Bag uses the same valid provider identity through claim, acknowledgement and renewal.
- Seizure presentation validates ownership where it is available, allowing remote client renderers to use the existing epoch/session guards.
- HPMK callbacks separate ACE's body-part/class strings from internal inventory/automatic-cleanup parameters.
- Facility/evacuation positions preserve numeric coordinates and parse string coordinates only, with type/finite validation.
- Adds B206 regressions to the existing network CI gate and a Windows deployment helper. Public version remains 1.2.4.1.

## Validation

- All 71 new B206 executable cases pass, including 29 Direct Pressure handshake/reconciliation cases. Running the new handshake and pending-reservation checks against the original B205 source reproduces the failures.
- Integrated relevant suites: **324 passed, one pre-existing surgical-airway failure**. The same testcase fails in the recorded B205 baseline: `test_confirmed_lifecycle_20260922::test_rejected_surgical_start_never_reserves_and_retry_works[ACM_core_ContinuousAction_Active = true;]`. The full historical suite was not rerun for B206; the documented B205 backlog remains.
- The 74-check network/ownership gate passes. The native-state ownership diagnostic reports zero direct Extended writes in the four audited native domains.
- HEMTT 1.22.0 check and `release --no-bin --no-archive` pass, producing 14 PBOs, 14 signatures and one key. Zero source errors/warnings; seven existing style-help diagnostics remain.
- Older execution fixtures now supply missing engine boundaries for net IDs, frame number, interaction distance, client identity and local provider/player checks. These changes allow existing pressure/handoff assertions to execute; they do not replace the production decisions with hardcoded success. The Hang Bag fixture also uses the current DP section delimiter.

Actual-source tests use SQF-VM v2026.04.03-ed9f5f5 and pytest 9.0.2. They simulate engine objects, clocks and event delivery; they do not run Arma's network stack or animation renderer. No live bandwidth/FPS or Windows asset-binarization result is claimed.

## Deployment and dedicated-server retest

Run `tools/Deploy-ACME-B206.ps1` from the updated branch at `F:\ACM-Extended`. It runs `hemtt check` and `hemtt release`, verifies the complete signed release, and copies `.hemttout\release` to the installed mod folder. Use its optional `-ModPath` and `-ServerKeysPath` for existing alternate destinations.

Install the same release on server and clients, restart the mission and check the B206 marker. Test Direct Pressure on server-owned AI, another player and yourself; repeat with an HC-owned AI if used. Check torso and limb sites, a second medic competing for the same site, stop/restart, and delayed cancellation. Confirm the pressure hold starts and no stale-claim timeout appears. Test Hang Bag admission/renewal and HPMK prep/remove. Windows asset binarization and live dedicated-server validation remain required on the deployment machine.
