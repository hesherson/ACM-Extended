# Stable 1.2.4.1 B210 downed-patient AI protection

Base: `653c746489895be8b3e9e2e4027cb938c33b623a` (B209).
Public version remains `1.2.4.1`; runtime/package identity is `B210 | NA8-B210-1.2.4.1-stable`.

## Problem and correction

ACE protects unconscious patients through its aggregated `setHidden` status effect. In the supplied ACE implementation, that effect sets camouflage to zero and asks hostile groups to forget the target. It does not change the patient's faction or captive status.

ACME can deliberately wake a patient while retaining a weapon-disabled medical lying position. ACE correctly removes its unconscious reason on waking; without a separate reason, that awake-but-still-down patient loses the protection. B210 gives ACME one reason, `acme_medical_downed`, alongside ACE and other modules' reasons. Removing ACME's reason cannot clear another module's protection.

Eligibility is owner-authoritative: a living ACE-unconscious patient, or a conscious on-foot patient with the medical lying flag and a specifically supported noncombat patient animation. Ordinary prone combat, upright obtundation, awake vehicle occupants, provider animations and conscious AAJT collapse do not qualify. The Semi-Fowler patient animations explicitly disable weapon/trigger input. Supported awake holds are ACM lying, ACME obtunded-back, ACM recovery position, the default ACE face-down pose, and the three Semi-Fowler patient states. The two exact chest-flip roll transitions qualify only if their loaded, inherited animation configuration disables weapons and trigger input; arbitrary mission-configured animations do not receive an exemption.

Get Up, animation changes, firing, full heal, death and respawn reconcile or retire the reason. Reset and firing exclusions apply to the current lying episode and follow ownership changes. Validated persistence completion starts reconciliation of the restored episode, including unconscious-to-unconscious restoration. Former owners remove only their local callbacks and registrations; they do not clear the patient's replicated effect on behalf of the new owner.

## Network and performance behavior

- The server seeds the new reason after ACE initialization. Clients wait for that shared reason list, avoiding simultaneous ACME reason-index allocation.
- Existing patient ownership registration and the existing one-second maintenance sweep drive repair. Only registered unconscious/lying patients are revisited. No new per-patient per-frame handler or recurring world/group scan is added.
- A new owner replays the existing aggregate effect once per ownership generation. Duplicate registration does not keep replaying it.
- A joining machine announces readiness once. Existing owners coalesce announcements and replay current aggregate state, limited to one observer/overwrite repair per patient per five seconds.
- A nonzero camouflage overwrite is repaired through ACE's effect handler at that same bounded cadence. Unchanged patients produce no recurring effect broadcasts or group scans.

B210 does not assign civilian side, set captive, grant invulnerability or introduce an AI targeting loop. It retains the normal damage model and ACE's own effect composition/restoration.

## Validation

- **1,661 required checks pass:** 75 ownership, 897 network execution and 689 behavioral checks. These include 60 new AI-protection and lifecycle cases, with actual production hooks and supplied ACE status-effect code.
- **Review reproductions:** the initial B210 implementation failed an executed healthy-reset-to-fresh-lying case; the correction now passes. Review also identified reset/locality and unconscious-restore gaps in that implementation; execution cases cover the corrected paths. Medical pose coverage includes negative checks for ordinary combat/provider poses and weapon-capable roll configuration.
- **Build/package:** HEMTT 1.22.0 `check` and `release --no-bin --no-archive` pass. All 14 PBO signatures, all 14 B210/protocol/component config stamps and the signing key verify. The strict native-state ownership audit reports zero violations in its four audited domains.
- **Complete frozen-source run:** 6,170 passed, 332 failed, 45 errors and 29 skipped by JUnit testcase identity. All 39 changed/new non-documentation files remained unchanged through the run. Pytest's console has one additional passing parent and failing subtest, as documented in B209; the comparison preserves testcase identities and duplicate occurrences.
- **Regression comparison:** passes against both B209 and the original B204/main baseline, with no newly failing, skipped or missing cases. Against B209, exactly 60 new cases pass; the same 377 inherited failure/error records remain. The full suite is not green, and baseline equality does not certify assertions blocked behind inherited fixture failures.

See [machine-readable validation summary](2026-09-30-b210-results.json).

## Practical limits

The execution tests run the new production functions and the supplied ACE bitmask, status-effect and visibility code. Engine objects, animation notifications and network transport remain explicit fixtures; this does not execute real Arma AI, native network delivery or animation rendering.

ACE only invokes `forgetTarget` when its receiver observes nonzero camouflage. Replaying an effect where camouflage is already zero does not guarantee that an AI mod's forced targeting or existing engine target knowledge is cleared. B210 closes ACME's identified state/lifecycle gaps; it is not a definitive fix for every AI-mod interaction or ongoing burst.

The historical full test suite has inherited failures; its baseline comparison is separate from the required all-pass gates. B209's documented mid-push Hardcore ownership-transfer limitation also remains unchanged.

## Dedicated-server acceptance

Install the complete same B210 build on the server, clients and headless clients, and restart them. Verify the B210 debug marker on each machine.

1. Observe enemy AI against a newly unconscious patient, then wake the patient into medical lying. Confirm the AI stops selecting the casualty and that Get Up restores normal targeting.
2. Exercise supported Semi-Fowler, chest-seal front/back positioning and the supported lying poses while awake. Ordinary prone combat and upright obtundation must remain targetable.
3. Exercise Get Up, full heal, death/respawn and saved-state restore. A fresh conscious Supine action after reset must receive protection; an old reset or fired lying episode must not regain it.
4. Transfer patient ownership between server/client/headless client, including away/back; join a new client while casualties already exist. Confirm current protection and normal restoration after recovery on all machines.
5. Repeat under representative unit counts, with the normal AI mods and without them if forced targeting persists. Check RPT errors, server frame time and traffic during mass casualties, joining and recovery.

Deploy from the updated branch with `tools/Deploy-ACME-B210.ps1`. Linux package validation does not execute Windows asset binarization; the deployment script runs the Windows HEMTT release build before copying its files.
