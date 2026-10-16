# B276 — Oxygen gate and native transfusion presentation

Candidate **1.2.4.1 / B276**, protocol **1**, based on B275 `495d77697c7e39052d1c8b9fdebb4fde5349ccff`.

## Native acceptance

1. Open the Ventway Sparrow without a usable ACM oxygen tank. Select FiO₂ on the parameters screen and on the legacy oxygen screen; both must show `An O2 tank is required.` Dismiss using OK, Enter and Escape, then change respiratory rate, tidal volume and PEEP. These controls must remain available.
2. Repeat with a loose charged tank, an empty tank and supported EFAK supplies under each configured provider/patient equipment-sharing mode. Only a real usable cylinder authorizes FiO₂ editing. A medical vehicle alone must not authorize it.
3. Start editing FiO₂ with a tank, remove the tank, and turn the adjustment control again. The stored/UI value must remain unchanged and the requirement dialog must appear. Restore a tank and verify adjustment works within the existing 21–95% range.
4. Open the transfusion menu at 4:3, 16:9, 21:9 and 32:9, with small/normal/large interface sizes. Check rounded surfaces, native list text/icons, button readability, no square black overlay obscuring rounded corners, and no decoration stealing input. Compare with the approved connected-line concept.
5. Fill all lists past their visible row limits and scroll. Verify selection, actions, native scrolling and matching row backgrounds. Reopen with empty lists and with a roller-clamp popup; ensure no residual card/background overlays appear on the clamp.
6. Check existing body/access artwork and hit positions with left/right IV, EJ, IO and field IV. Run a Y set and piggyback secondary, prime/flush, attach/remove a warmer, prepare an infusion and cancel/complete a bag move. Repeat on a dedicated server with two clients and patient locality transfer.

## Automated evidence

The integrated focused run passed **579 cases and 5 logged subtests**, with no failures, errors or skips. It includes the production FiO₂ gate, native card clipping/scroll arithmetic, access-scoped metadata, existing ventilator/supply handling, line service, native menu actions, body geometry and clamp isolation. All **157 fork phase scripts** and the structural scan passed. Strict HEMTT validation checked **1,883 SQF files, 16 addon configs and 12 stringtables**. The owner-write audit and whitespace checks passed.

All ten new PAA textures preserve transparent corners and opaque centers after native round-trip conversion; total size is 23,067 bytes. The standard body-map artwork, overlays, roller-clamp dialog, 16 related functions and two clamp artwork assets match B275.

Full remote CI and final frozen signed-package verification are separate checks. Native Arma rendering, input and multiplayer acceptance remain unexecuted. Source/VM tests and offline texture checks do not establish native visual acceptance.

## Deployment

With Arma closed, use the existing `F:\ACM-Extended` checkout and `tools/Deploy-ACME-B276.ps1`. The helper retains preflight, explicit build identity, strict HEMTT checking, signed release creation and journalled installed-file verification. Use matching complete B276 packages on every participant.
