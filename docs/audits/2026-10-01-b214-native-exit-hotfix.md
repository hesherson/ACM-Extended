# Stable 1.2.4.1 B214 native exit hotfix

Base: B213, `23b27fb090a5adc4b67989279273c12631ad5c09`.
Public version remains **1.2.4.1**; runtime and every package component identify as **B214**.

## Reported failure and cause

The user's screenshot reports `No entry 'bin\config.bin/CfgMovesMaleSdr/States/AinvPknlMstpSnonWnonDnon_medicEnd.connectFrom'`.

B213 reopened that native state with a concrete class body but no inherited base. Arma's empty-base syntax removes the existing inheritance, so inherited move properties disappear even though HEMTT accepts the config. Adding a lone `connectFrom` array would mask one symptom while leaving the other inherited properties absent.

B214 replaces that override with an external forward declaration. BI's complete native state and outgoing graph are preserved. The custom pressure hold and chest workspace still link into the requested literal `medicEnd`; the provider controllers still request it at 1.5x. No guessed parent, copied native RTM definition, or replacement animation is introduced.

The uploaded ACM sources already use the literal native exit without redefining it. The uploaded ACE and Animate packages do not define a replacement for this state.

References: [Bohemia class inheritance, including Empty syntax](https://community.bohemia.net/wiki/Class_Inheritance) and [Bohemia Arma 3 move names](https://community.bistudio.com/wiki/Arma_3%3A_Moves).

## Native completion timing

Review of the restored native exit path reproduced another bounded issue. If the first observed frame of `medicEnd` already has 0.3 seconds of native progress, a clock starting at that observation undercounts the move. On the subsequent transition into native kneeling idle, the chest sequence can incorrectly classify a completed exit as an interruption and skip the carrier-restoration reach.

The controller now anchors its fallback clock to each valid native elapsed-time sample. Native elapsed time remains authoritative while the move is visible; its last valid anchor carries across the transition to idle. The original completion threshold, movement cancellation, ownership guards, and unrelated-motion rejection remain in place. Early idle does not count as completion. The carrier gate cannot release early merely because the wall clock advanced.

Direct-pressure holstering, animation ownership, prone handling, respiration observation, airway timing, debug presentation, and clinical physiology are unchanged by this hotfix. No automatic weapon restoration is added.

## Verification

All **2,216 required checks pass** (75 ownership, 1,452 networking/feature execution, 689 behavioral), plus 24 version-related regressions. HEMTT check and release pass. All 14 PBO signatures and B214 component stamps verify; the strict native-state ownership audit reports zero violations. Raw reports and compiled-package checks are retained in `2026-10-01-b214-test-reports.zip`; exact counts and source hashes are in `2026-10-01-b214-results.json`.

The nine new source-structure cases reject the actual shipped B213 declaration and its array-append mutation, reject attempts to hide an inheritance reset by adding one missing field, and permit safe external references. Eleven new execution cases cover delayed observation, natural idle completion, early interruption, movement, successor treatment/token ownership, native timing versus wall time, and invalid elapsed samples.

The signed package's decompiled config is checked independently of source spelling: `medicEnd` remains an external reference and every concrete ACME provider state retains an explicit base. All 29 SQF files reviewed for the B213 feature batch are compared byte-for-byte against their current B214 package contents.

The historical full suite is not rerun for this narrow hotfix; its previous B213 outcomes remain recorded in the B213 audit. These checks do not execute Arma's live config merge, render RTMs, or reproduce multiplayer. Linux release verification uses `--no-bin`; the Windows deployment helper runs normal `hemtt release` with asset binarization. Restart Arma and use the same complete B214 build on clients and server.
