# B263 — mod-heavy multiplayer chest/thora acceptance (candidate)

## Code issues addressed
- Stale ACE and ACME medical-menu PFHs could still call closeDialog during a modal handoff.
- Thoracostomy abort and missing-window cleanup used only partial equipment-lease release.
- Chest Seal preparation could await an owner response without a deadline, and a provider could silently lose an opening when the owner moved.
- Legacy ApplyChestSeal / PerformThoracostomy actions could go through the wrong treatment/animation callback.

The B201 RPT's `no anim [ApplyChestSeal, animationMedicSelfProne]` identifies a legacy action path; by itself it does not prove a specific packet loss. B263 routes the deprecated launcher through canonical clinical predicates and suppresses its irrelevant AI animation.

## Mandatory live validation
Use B263 on the dedicated server, at least two clients and HC. Match all PBOs, keys and network protocol; retain server/client/HC RPTs. Repeat on the operator's full modpack:

1. Living and dead spawned patients, with/without carrier, active Semi-Fowler or CPR. Start chest seal, NAR SPEAR, new thoracostomy and Adjust Thoracostomy; verify one modal appears, no one-frame flicker or missing interface.
2. Medic client targeting another client, headless-owned patient, server-owned AI, Zeus/local-controlled NPC. Change patient locality while preparing; operation must either use the acknowledged owner or cancel cleanly with a retry message.
3. Two medics simultaneously on one casualty: no duplicate patient chest roll, gear, damage effect or clinical debit; each closed dialog cleans its own session without disrupting the other's.
4. Stress 20 rapid open/Escape/F0/reopen cycles; close at every preparation stage. Check keys, carrier, crouch, animation speed, input and other medical menus still work.
5. Simulate loss of an owner acknowledgment / owner disconnect; no indefinite Preparing—bounded chest retry and 30-second abort, thoracostomy timeout at 20 seconds.
6. Delayed stale panel Unload after a new thoracostomy dialog opens must not close the replacement or release its lease.
7. Re-enable old class names via another addon and verify requests route through ACME's current clinical checks; overwriting ACE's treatment bridge must trigger `[ACME COMPAT] FAILED`.
8. Test same vehicle and different vehicle, very low FPS, UI scale changes, dead patient and suddenly removed patient, and simultaneous unrelated IV/vent/transfusion UI. Capture logs tagged `[ACME MODAL B263]`.
9. Compare expected chest/thora physiological effects and supply debits after successful actions; a retry or cancel must never make an extra clinical transaction.

Run full CI regression/ownership gates and Windows HEMTT check, release/signatures. No source-level test or CI suite can guarantee compatibility with arbitrarily conflicting addons. If a mod overrides ACME's mandatory treatment bridge, resolve the conflict before deployment; never silently force-override the other mod.
