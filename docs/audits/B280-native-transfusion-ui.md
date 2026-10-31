# B280: native transfusion controls and prepared-set placement

Version: **1.2.4.1 / B280**, network protocol **1**. Baseline: `7893d55926269e9b70243aad378de25f86b77d2d` (B279).

## Evidence and changes

The supplied native RPT contains two `SwitchTargetInventory` parameter errors. The menu opener passed its inherited `[medic, patient, bodyPart]` arguments into a Boolean parameter. Native initialization and the inventory switch button now pass explicit empty arguments; the function also accepts native event payloads without a type error, while `[false]` remains a refresh of the current source. Typed SQF parameters substitute their default after a type mismatch, so the RPT error alone does not establish that inventory initialization stopped or caused either reported input failure.

The native Y button retains its `RscButton` action and sound inheritance. Its enabled state depends on an eligible selected blood row, available tubing and idle preparation. The inventory card's hit control now draws after its decorative children, and both the card group and its hit control are explicitly enabled. These changes protect the native selection path. They do not constitute an observed Arma pointer/sound test.

The screenshot confirms the tab styling regression. Inventory lacked a rounded frame; Prepared IV sets painted an opaque rectangular fill over its frame. Both now use transparent native button faces and matching rounded, neutral grey nine-slice surfaces. Their selected state follows the active inventory/prepared pane. Existing body/access artwork, action bindings and card geometry remain in use.

B279 used one mass-18 carrier for every prepared fluid set. This made spiking a personal 500 mL bag plus mass-0.1 IV line increase the replacement load from 5.1 to 18. The return path also used the aggregate soldier load limit, unlike ACE's own inventory placement. B280 selects bounded carrier classes from the actual supported source-item masses plus the administration line or Y tubing, uses ACE-compatible capacity admission, and verifies native placement. The exact carrier class follows its registered token through reservations and returns. Unmapped third-party mass totals retain the legacy class.

True overflow or a failed provider addition places the same identity in a ground holder with a placement notice. A failed placement retains funded pending custody instead of announcing a carried set. Spike/build messages no longer claim that registration has already completed. Carrier magazines also disable ACE repacking, which would otherwise rewrite their opaque ammo identities.

The RPT does not record the provider's inventory load or post-spike cargo. A capacity spill is a demonstrated source-code path, not a proven explanation for this particular session. The disappearance and native input symptoms must still be checked in Arma.

## Regression evidence

The new checks execute the production native opener call sequence, inventory builder, card selection handler and preparation admission predicates before the actual three-step Y action. They also cover carried/ground/pending prepared placement, mass selection, exact carrier removal/return, transfer and adoption, and decoded shipped tab textures. Native inventory/config/UI commands are represented at their engine boundaries. All B279 test identities and modules remain required, alongside strict HEMTT validation, the retained CLI gates and signed-package audits.

The build identity is logged once at startup. Changed Y-input states are logged at most 16 times per opened display under `[ACME B280 TX]`, including the selected source/row/item, tubing count, busy flags and the final native shown/enabled state. Unchanged refreshes stay quiet.

## Arma acceptance

1. Open the actual modpack's transfusion menu with no access and with torso FAST1. Select an eligible blood card. Confirm the Y button receives mouse input and its native sound, then complete **Spike Y tubing → Select Flush Saline → Build Y Tubing**.
2. Spike a personal saline bag in a nearly full kit. Confirm the prepared set appears after allocation, its mass matches the replaced bag and line, and both tabs have rounded grey styling. Repeat for supported premixed carriers and blood/saline Y combinations.
3. Force actual capacity overflow. Confirm the notice and ground carrier, pick it up and verify the exact prepared contents appear. Move a weighted carrier through Gear to another medic, then prepare/hang it and exercise a rejected operation's exact return.
4. Use identical complete B280 packages on the server, clients and headless clients. Confirm the startup build marker and inspect the bounded input trace if an action is still unavailable.

## Windows deployment

Close Arma and local servers, fetch the tested B280 commit into the existing `F:\ACM-Extended` checkout, then run:

```powershell
Set-Location F:\ACM-Extended
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B280.ps1
```

The helper checks the clean source/build identity, performs strict validation and native release packaging, then deploys through the existing journalled installer. Confirm **1.2.4.1 / B280** in game.
