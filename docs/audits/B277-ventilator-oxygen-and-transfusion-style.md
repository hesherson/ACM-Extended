# B277 — Ventilator oxygen and transfusion styling

Candidate **1.2.4.1 / B277**, network protocol **1**, based on B276 `66afbe91d3cb3ca7e1be11c4347b62cc63e1f90d`.

## Scope

The Ventway Sparrow continues to ventilate with ambient air and battery power. Oxygen enrichment requires an available portable oxygen cylinder. Oxygen availability controls only FiO2 adjustment; pressure, respiratory rate, ventilation mode and other existing settings retain their own procedure-tier and Simple-mode rules. Simple ventilation keeps automatic settings while exposing manual FiO2 when oxygen is available.

The existing O2 page attaches a cylinder through the established provider/patient equipment-sharing order, reports available reserve and gates FiO2 editing until the source owner verifies it. Attachment does not consume the cylinder. Actual delivered inspiratory gas consumes finite reserve through owner-certified inventory requests and prepaid gas credit; paused ventilation and a 21% setting do not draw enrichment gas. Depletion, source loss or insufficient paid credit gives effective 21% room air while preserving battery-powered ventilation and the requested setting. A stored device setting or snapshot cannot restore spent gas. Manual breaths carry a monotonic provider sequence and an owner-published high-water record scoped to the patient epoch, device custody and ventilation episode. An accepted breath cannot become replayable when the bounded receipt list evicts it after later commands or patient locality changes.

The transfusion menu receives native rounded panel styling and spacing closer to the approved preview. It retains the existing ACM body image, IV/IO and fluid artwork, body-site selection, prepared-set and infusion workflows, bag actions, connected-line indicators and roller-clamp popup. Black and grey surfaces carry the menu; temperature and connected-line roles retain their existing limited color cues. Nine-piece native surfaces preserve circular corners across screen ratios, and a fixed pool of twelve reused cards delegates to the existing lists using physical bag or prepared-set custody identity. Wheel and keyboard navigation move the viewport without discarding supplies or selecting a stale neighboring row. Narrow cards stack the complete piggyback role and warming indicator above their progress bar, and native button focus remains visible. The Prepared IV Sets toggle keeps a transparent native overlay so repeated refreshes cannot cover its rounded background with a square fill.

B277 incorporates the concurrently published B276 source and its subsequent fixture corrections at `66afbe91d3cb3ca7e1be11c4347b62cc63e1f90d`. The B276 case identities and native artwork remain present; their supply and surface checks follow the stronger attached-cylinder and custody-bound card implementations.

This candidate remains on stable 1.2.4.1 and protocol 1. It does not constitute native Arma or dedicated-server acceptance.

## Automated evidence

Integrated validation passed **227 focused cases**: 136 new oxygen transaction, oxygen UI and native card cases, plus all 91 retained B276 supply/surface cases. Production SQF executes native cylinder reserve/debit, provider/patient donor order, compatible EFAK supply, attach/probe/draw/ACK retry and replay, state loss and transfer, finite prepaid delivery in advanced and Simple ventilation, actual spontaneous CPAP delivery, manual-breath high-water admission, only-FiO2 UI authorization, exact card custody, stale metadata guards, keyboard/wheel navigation and aspect-correct rounded geometry. In both manual paths, an early accepted command remains rejected after 65 later rejected commands, a fresh higher sequence can succeed, and eviction from the 64-entry receipt history cannot recreate the old breath or debit. Native rendering, scheduling and real multiplayer transport remain outside these fixtures.

The complete reviewed current selection passed **5,709 cases across 203 modules**, with zero failures, errors or skips. Four bounded parallel parts covered the selection; complete affected-module reruns replaced obsolete engine-boundary fixture outcomes after integration. Every replacement report was checked against fresh collection for the entire affected module. An independent final collection matched all 5,709 executed case identities exactly, with no missing or unexpected case. One new prepublication card case expanded into adverse parameterized cases; no published B276 test identity was dropped. The broader historical comparison is a separate CI gate.

The affected historical Simple ventilation, dead-patient device, NIV and interaction suites passed **231 cases and five subtests** after loading the new oxygen helpers at the existing engine boundaries. Their procedure, replay, manual-breath, airway, circuit and NIV guards remain active. The merge-affected line-service, provider flow, layout, build identity and strict native-owner test suites passed **299 cases**. The complete retained B50 module passed **10 cases** after executing current prepared-custody identity capture and the transparent native overlay. These sets overlap the reviewed current selection and are not additive totals. An independent older-feature review also passed 483 cases and 170 subtests across 30 affected historical modules.

`PYTHONDONTWRITEBYTECODE=1 python tools/validate_fork.py` passed **157/157 phase scripts** and scanned **1,903 SQF files / 14 addon configs**. Final strict HEMTT checking passed: **16 addon configs, 1,903 SQF files and 12 stringtables**. The strict native writer audit found zero violations, and `git diff --check` passed. All 63 new power-of-two PAA surface pieces round-tripped through HEMTT, retained their alpha corners and regenerated byte-identically with recorded hashes; they total 105,742 bytes. Offline 4:3 and 16:9 layout composites and additional aspect checks passed without ordinary text clipping. These are asset and geometry checks, not rendered Arma acceptance.

Linux signed packaging remains pending until the final source commit is frozen. Its signature and embedded-commit verification must be reported separately; native Arma execution has not been performed in this environment.

## Native acceptance

Install matching complete B277 packages on dedicated server, clients and headless clients. Source tests and SQF-VM fixtures do not verify native UI rendering, physical inventory behavior or real Arma locality.

1. Start ventilation with battery power and no oxygen cylinder. Confirm room-air ventilation remains available and only FiO2 adjustment is restricted by the missing oxygen supply. Repeat in Simple and advanced modes; existing automatic-setting and procedure-tier restrictions must remain intact.
2. Supply a partially charged cylinder through each supported inventory source, attach oxygen and adjust FiO2 between 21% and 95%. Verify the displayed reserve, actual effective FiO2 and oxygen consumption. Setting room air must not consume enrichment reserve.
3. Empty or remove the active oxygen source during ventilation. Confirm effective FiO2 returns to room air while ventilation continues on battery power. A stale editor must not restore enrichment without a valid supply. Disconnect/reconnect and replace a cylinder without duplicating or restoring spent oxygen.
4. Race oxygen attach, removal and adjustment from two providers and repeat after patient/provider locality transfers. Confirm owner validation settles each request once, custody remains exact, and unavailable providers cannot commit later. Replay an accepted manual breath after many later rejected commands and a locality change; it must not create another delivered volume or cylinder debit.
5. Open transfusion at 4:3, 16:9, 21:9 and 32:9 with IV, IO, EJ, Y tubing, piggyback and warmed fluids. Check rounded surfaces, native artwork, text contrast, centered patient identity, outward tags, coherent spacing and control hit targets. At narrow 4:3 sizes, confirm the full Piggyback Primary/Secondary and LW Quantum warming text remain readable above the progress bar. Use Tab focus, arrows, Page Up/Down, Home/End and the wheel; selection must follow the same original custody and the visible focus frame. Reopen repeatedly and check for overlapping first-frame controls, square fills or drift.
6. Repeat Y preparation, prime/flush, piggyback preparation and attachment, medication preparation, warmer add/remove, and connected bag moves. Verify B275 behavior and custody are preserved, including pending moves that remain attached when the menu closes.
7. Open the roller clamp and exercise wheel, drag, pause/resume and drop selector. Confirm the retained popup and bottom statistics remain correct and the new panel artwork does not intercept input.

## Deployment

`tools/Deploy-ACME-B277.ps1` retains the journalled deployment flow: preflight, B277 identity verification, strict HEMTT check, signed release build, installed-file hash verification and recovery. It rejects source edits without discarding them and deploys into the existing checkout and `.hemttout\build` location.

```powershell
Set-Location F:\ACM-Extended
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B277.ps1
```

Supply `-ServerKeysPath` only for an existing separate dedicated-server keys directory. Confirm 1.2.4.1 / B277 in-game and use matching complete packages on server, clients and HCs.
