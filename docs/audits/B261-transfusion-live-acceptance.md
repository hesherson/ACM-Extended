# B261 — Transfuse Fluids targeted multiplayer verification

**Candidate:** ACM Extended stable 1.2.4.1 / B261; network revision NA8-B261-1.2.4.1-candidate.

B261 addresses two source-confirmed problems: the Adjust Infusion action overlapping ordinary fluid rows, and active infusion list rebuilds on every fluid-volume change. This checklist needs an actual Arma 3 dedicated-server run; CI alone cannot certify UI geometry on varied aspect ratios.

## Setup

- Server, two clients and any headless client must all run the exact same B261 addon set. Record in-game overlay batch and client/server RPT logs.
- Start with a clean casualty. Establish two IV sites on the same limb or left/right EJs.
- Test at the player's usual UI scale, plus small/large UI scales and a different aspect ratio if practical.

## Live acceptance

1. Open **Transfuse Fluids** with no bags: ordinary fluids list and available inventory list retain distinct rectangles; no buttons obscure another control; page navigation and access hotspots respond on first click.
2. Hang two different bags onto separate IV/IO accesses. Select each site; verify only that line's bags appear and are labelled by their actual remaining physical volume.
3. Start a drug-in-saline infusion. The main fluids pane shrinks; **Adjust Infusion** occupies its own row between regular fluids and the active-infusion title; no rows or buttons overlap.
4. Observe an active infusion for 20+ seconds. Its mL value must decrease as actual fluid drains, the tooltip must agree with the current physical bag, and the selected row must remain selected through mL-only updates.
5. Pause and resume flow. The status may change and force one structural reflow, but it must never flicker every 0.25 seconds, reset selection, or double-invoke an action.
6. Use a Y-line with saline and blood, switch access, prime and flush, remove/replace bags. Both main-bag and medication-infusion labels must reflect their own physical volume, without an obsolete [Y]/temperature tag.
7. Repeat with the roller-clamp window, Narc Box, and infusion controls open/close cycles; no stale modal lock, dead button, runaway list rebuilding, or wrong-target inventory updates.
8. Disconnect a remote provider or switch casualty locality during a flowing infusion; any user interface on the remaining client must rebind to the correct actual patient and not show a fabricated unchanged value.

## Release gate

- GitHub B261 strict-full-suite and static validation green; no new/current test failures.
- Re-run the broader 13-case dedicated-server clinical/network acceptance checklist in `docs/audits/B257-dedicated-server-acceptance.md`, including the B258/B259 chest-tube, airway, CPR, slow-calcium and 40-BPM SIMV changes.
- No RPT errors, UI overlap, duplicate infusion rows, stalled remaining-mL values, leaked worker, or lost action selection.
- If a visual error persists, capture a screenshot plus client UI scale/aspect ratio and the access/bag setup. Do not claim public-release approval solely from CI.
