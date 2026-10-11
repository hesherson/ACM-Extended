# B275 — Connected transfusion menu

Candidate **1.2.4.1 / B275**, network protocol **1**, based on B274 `7c2dc25b997b18618770d95845d5c63d8a561731`.

## Scope

This candidate applies the approved transfusion concept to the native Arma menu. The existing body image, IV/IO/EJ artwork, fluid icons, access selection and roller-clamp controls are retained. Black and grey panels carry the menu, while fluid temperature and connected-line roles supply the limited color cues. The patient name is centered and the blood type beneath it starts at `???`; it becomes known only after this provider checks this patient's dog tag. Access captions use short forms such as `20G IV`, `20G IV + extension` and `18G field IV`. Occupied-access tags lead outward from the body with a diagonal joining the rectangle's top edge.

Blood preparation defaults to Y tubing; the dropdown retains ordinary bag spiking. Prepared bags do not appear among the patient's active fluids before owner-accepted attachment. Prime Line starts the new Y line when priming completes. The primed line offers Flush Line only while its reserve saline bag is selected, and that bag is labeled Reserve Flush Saline. The bag list identifies connected bags with `[Y]` or `[PiB]`.

Bag Actions starts a piggyback workflow against the exact selected access and existing primary bag. Only compatible nonblood fluids or saline-carrier infusions may be added. The secondary runs by gravity before the primary, which is held while the secondary remains active. Prepared selections use Add to Piggyback, and medication preparation uses the established infusion workspace. Canceling a selection or changing access releases the temporary workflow without losing prepared supplies. The two connected rows remain independently selectable and carry Piggyback Primary / Piggyback Secondary indicators with a distinct light purple bracket.

A Lifewarmer Quantum sits downstream of the connected access, so attaching it through either Y or piggyback row warms whichever branch is currently flowing. It consumes one device for the connection, and Remove Fluid Warmer returns one device immediately. Add Fluid Warmer requires an explicit inline Yes/No when the provider has only one available warmer. Saline warming caps an otherwise faster flow at **200 mL/min**; plasma warming caps it at **100 mL/min**. A cap never raises a slower flow. Warmed fluid names and `LW Quantum · Warming...` use the same orange, and the ellipsis advances at one-second intervals.

Move Bag retains patient attachment until a destination is selected and accepted by the owner. Closing the menu or canceling a pending move must leave all connected bag custody intact. This change stays on stable 1.2.4.1 and does not change protocol 1.

## Automated evidence

The initial B274 targeted baseline passed **56 tests**, covering build identity, menu geometry, preparation transitions and roller-clamp redraw. Initial HEMTT strict checking compiled 1,853 SQF files, rapified 16 addon configs and checked 12 stringtables. These checks occurred before feature integration and are baseline evidence only. Final B275 results are recorded below after integration.

Integrated validation passed **201 focused B275 cases** through production SQF and native geometry. These execute branch priority and medication mass balance, native 16/18/20g gravity without Hang Bag/cuff boosts, admitted-volume heating and caps, prime completion and owner flow, exact reserve click guards, read-only labels and one-second dots, UID resolution after reordering, captured move callbacks and tokens, connected moves, warmer receipts/locality recovery/snapshot custody, outward tags and observer blood-type knowledge, and exact-access preparation returns. The owner attachment suite executes the native carrier factory and medication registration, including exact replay, altered request identity, delayed escrow publication, stale epochs, unavailable providers/patients, replaced primary bags, failed carrier creation and partial medication rollback. The historical line-service suites passed **249 cases**; two affected B271 snapshot cases also passed after adding the new helper and publication-cache fixtures. Build identity, native writer audit, offline compile closure and updated thermal/dependency contracts passed **66 cases**.

The complete reviewed current selection passed **5,482 cases across 198 modules**, with **zero failures, errors or skips**. Four bounded parallel parts covered the selection; explicit affected-module reruns replaced obsolete fixture outcomes after integration. An independent final collection matched all 5,482 executed case identities exactly, with no missing or unexpected case. The earlier single-process run exceeded its 600-second limit and is not counted as a passing run. The broader historical before/after comparison is a separate CI gate.

`PYTHONDONTWRITEBYTECODE=1 python tools/validate_fork.py` passed **157/157 phase scripts** and scanned **1,882 SQF files / 14 addon configs**. Strict HEMTT checking passed after integration: **16 addon configs, 1,882 SQF files and 12 stringtables**. `git diff --check` passed. Linux signed packaging remains pending until the source commit is frozen; its signature and embedded commit verification must be reported separately. Native Arma execution has not been performed in this environment.

## Native acceptance

Install matching complete B275 packages on dedicated server, clients and headless clients. A source test, SQF-VM fixture or Linux package cannot verify native control rendering, physical input or real Arma locality.

1. Open the transfusion menu at 4:3, 16:9, 21:9 and 32:9 with left and right IVs, multiple gauges, field IVs, EJ and IO. Verify the native body and overlays, occupied-only outward tags, seamless top border, concise access caption, centered patient title and neutral panel colors. Repeat with all six body parts and both access types; check tag collisions and hit targets.
2. Before checking a dog tag, confirm Blood Type: ???. Have one provider check it and confirm that only that provider learns the type. A second provider must still see ??? until they check the tag. Reopen both menus, change patients and repeat after locality transfer; unknown cached patient state must not reveal the blood type.
3. Spike blood using the default Y action, select only eligible saline for its reserve, finish preparation and confirm the view opens Prepared IV Sets. A direct Spike Bag remains available in the dropdown. Nothing should appear under patient Fluids until Hang Set is accepted. Repeat with disappearing supplies and rejected owner requests.
4. Hang a Y set. Confirm both independently selectable rows show [Y], the reserve row says Reserve Flush Saline, and Prime Line is present before priming. Complete priming and verify the primary starts flowing; saline spent priming is credited exactly once. Flush Line must appear only for the selected reserve saline. Confirm queued 50 mL flush increments, right-click cancellation and dirty-line gating remain correct.
5. Start Piggyback from a single nonblood primary. Verify incompatible inventory/prepared rows are filtered, compatible rows are highlighted, and blood/direct propofol are excluded. Spike a compatible carrier and confirm it becomes a prepared [PiB] set with Add to Piggyback. Inject medication through the existing infusion editor, then attach the prepared infusion without an extra IV-line debit. Cancel through another action or access selection and ensure supplies remain prepared.
6. Run a plain-fluid and a medicated secondary on separate patients. Verify secondary gravity flow, primary zero delivery, correct remaining volumes/dose delivery, and automatic primary resumption after secondary completion. Pause/resume both branches, attempt to open the primary early, remove access and transfer locality. No duplicate medication or fluid delivery may occur.
7. Add a warmer through either connected row. Both rows must display the same downstream device, with only the flowing fluid warming. Confirm one device is spent, and repeat with 0, 1 and 2 spare devices. With one spare, No/closing/changing selection must leave inventory intact; Yes spends exactly one. Two providers adding concurrently must not spend or fit two devices.
8. Warm saline at flows below and above 200 mL/min, and plasma below and above 100 mL/min. Verify the actual delivered volume obeys each cap without increasing lower rates. On a piggyback connection the held primary must stay at zero. At a branch transition the newly flowing fluid must obey its own cap and update orange fluid/LW Quantum text consistently. Remove Fluid Warmer through either row and verify one immediate inventory return, no repeated return after replay or double click, and no warming on another access.
9. Begin Move Bag and close the menu. Reopen and confirm the bag remains attached. Move connected Y/piggyback groups to a valid free access; verify all connected custody, infusion bindings, warmer and service state move together only after owner acceptance. Race the destination with another provider and confirm rejected movement preserves source custody.
10. Open the retained roller clamp for an infusion. Verify its wheel, drag, toggle, drop selector and bottom statistics, with no duplicate side readout. Repeat pause, depletion, clamp changes, secondary/primary transition and access removal. Confirm menu controls do not mutate the popup or steal its input.
11. Repeat all owner-changing operations with delayed/duplicate ACKs, packet delay, patient ownership transfer and a headless client. Confirm accepted operations settle once, rejected operations restore exact original prepared/supply custody, disconnected providers cannot commit later, and the menu refreshes without stale rows or recurring preparation debits.

## Deployment

Use the existing checkout and installed `.hemttout\build` location. `tools/Deploy-ACME-B275.ps1` preserves the journalled deployment: preflight, explicit B275 identity contract, strict HEMTT check, signed release build, installed-file hash verification and recovery. It rejects source edits without discarding them. It does not publish or merge the candidate.

```powershell
Set-Location F:\ACM-Extended
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B275.ps1
```

Supply `-ServerKeysPath` only for an existing separate dedicated-server keys directory. Confirm 1.2.4.1 / B275 in-game and use identical complete packages on server, clients and HCs.
