# B302: compact transfusion cards and functional flow cues

Candidate 1.2.4.1 / B302, multiplayer protocol 2. Baseline B301 `de71fb771a30ae4e3cc25e1c115b65e7753a47d2`. PR #31 remains draft and unmerged.

## Requested presentation changes

All five native list viewports use two 0.090-safeZoneH cards separated by the existing 0.007 gap. This restores the prior infusion-card height and makes the fluid cards thinner than B301's 0.1015 height. Fluid/infusion card and progress-track widths now match. Original readable square icons, labels, corners, colors, scrolling, selection identities and mirrored headings/action rows remain. The details/log panel returns to its compact left footer. Paired buttons use a 0.004-canvas gap, exactly matching the panel's left content padding. The Inventory hover tooltip explains Self/Patient switching and the existing occupied-vehicle source.

The running-state native button now says Pause IV Transfusion or Pause IO Transfusion. Its original config handler, owner dispatch, access validation and physical flow toggle remain. The existing Start wording remains when paused. No second click observer or flow mutation is added.

Ready Spike/Hang, Y setup, Give/Prepare/Inject/Infuse and Prime/Flush actions pulse only their rounded background opacity. Prepared IV sets pulses when records are available and its chooser is closed. The label, hit rectangle, visibility and focus remain fixed. Disabled, hidden and unrelated controls do not pulse. Existing service tint is retained.

The existing remaining-volume white line carries a moving diagonal stripe only while its physical bag is actually delivering. Native presentation exports an explicit Boolean through the bounded card snapshot. A clipped native controls group and a clipped React overlay reuse the same code-drawn stripe texture. Its width and its clipping endpoint follow measured fluid volume; the texture moves underneath without predicting consumption. Held primaries, stopped/clamped lines, detached bags, empty bags and absent perfusion remain still. Native stale data stops its animation within 0.75 seconds; React uses its existing session freshness/fallback fencing.

Graduation numbers increase gradually as the measured endpoint approaches. Native and React share a symmetric smoothstep curve, reaching 1.35 times normal size at the tick and returning to 1 at 70% of the neighboring-tick interval. Tick positions and spacing do not move. The React font-size transition is confined to the numeric label; the card, measurement track, textures and focus remain mounted and fixed. Added-medication dose captions and physical capacity are unchanged.

Y and piggyback branch arms now terminate at the actual card edge, giving the same horizontal length for bags and infusions. B301's live-UID anchors remain independent of hidden action-menu faces; removed bags drop stale endpoints. Existing IV/IO outlines, flags, site dots, body artwork and ACE menus remain unchanged.

## Performance and validation

The existing two idempotently registered UI workers remain two. The transfusion worker performs cached decoration at 20 Hz and gates expensive data/workflow refresh to the original 4 Hz. Tests execute the shared worker across 11 animation ticks, proving exactly 3 data refreshes and 11 decoration calls over 0.5 seconds, plus duplicate-registration rejection. The animation helper has no inventory discovery, patient/clinical reads, treatment dispatch, row selection or control allocation.

New production-code tests exercise the proximity curve on both sides of ticks at three graduation densities, clipped texture movement, held-primary exclusion, stale stop, stable card/hit geometry and bounded pools, equal track/connector widths, source tooltip, matching gaps, compact log, unchanged native handler and protected ACE/art scope. Existing geometry contracts follow the requested compact dimensions; historical scope checks remain pinned to their published snapshots. The browser reproduces the compiled local bundle at four compact pane sizes, checks actual stripe transform movement, numeric growth/taper, paused flow, font readiness, stable nodes/focus/textures, empty output and fallback.

Final test counts and signed-package hashes accompany delivery. Strict HEMTT checks 2,142 SQFs, 15 stringtables and 22 configs. Native-owner audit reports zero violations. The Node suite has 45 passing cases. Signing/packing verification covers all 19 addons, B302 stamps, exact packed source/texture files, compiled controls and source-patch tree reconstruction.

Arma cannot run in this container. Native clipping, font rasterization, pulse appearance, actual UI scales and live multiplayer treatment acceptance still need in-game testing. Browser checks are not native screenshots. Container packages omit Arma Tools model/animation binarization; the Windows helper runs native HEMTT release. Fully close Arma before replacing the complete build/key on server, clients and HCs. Preserve the persistence profile/adapter and avoid duplicate standalone DD1380. React remains experimental and OFF by default; no glass, world effect, new screen or ACE styling is introduced.
