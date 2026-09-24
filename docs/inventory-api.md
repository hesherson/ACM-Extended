# Medical supplies: ACME_fnc_itemCount / itemTake / itemList

ACM Extended's own windows and actions - chest seal, IV minigame and tray, syringe kit, laryngoscopy,
suction, thoracostomy, ventilator, transfusion, EMMA, vials, CPR with a BVM, AED, oxygen - read and take
the medic's and patient's supplies themselves instead of going through an ACE treatment. They do it
through three functions, so an inventory mod has one place to answer:

| Function | Arguments | Returns | Without an inventory mod |
|---|---|---|---|
| `ACME_fnc_itemCount` | `[unit, class]` | how many the unit can use `<NUMBER>` | `ace_common_fnc_getCountOfItem` |
| `ACME_fnc_itemTake` | `[unit, class]` | one was taken `<BOOL>` | the engine's `removeItem` |
| `ACME_fnc_itemList` | `[unit, mode]` | classes the unit has, modes as `ace_common_fnc_uniqueItems` `<ARRAY>` | `ace_common_fnc_uniqueItems` |

Rules for new code:

- Count a unit's supplies with `ACME_fnc_itemCount`, never `ace_common_fnc_getCountOfItem` or
  `'class' in (items _unit)`.
- Take a supply for a treatment with `ACME_fnc_itemTake`, never `_unit removeItem`.
- Pick from what a unit has with `ACME_fnc_itemList`, never `ace_common_fnc_uniqueItems`.
- Moving items between places that are not a treatment - the blood cooler - stays with the engine
  commands. So does AI healing (`core/overrides/fnc_healingLogic.sqf`, `fnc_itemCheck.sqf`) and the gas
  mask.

## Enhanced First Aid Kits

With [Enhanced First Aid Kits](https://github.com/MissHeda/FAK-standalone) (EFAK) loaded, an IFAK, AFAK
or MFAK is one inventory item with virtual contents. The three functions ask EFAK's public API when it
exists, so everything packed in a kit the mission lets treatments use counts and is taken straight out
of the kit:

| ACME | EFAK |
|---|---|
| `ACME_fnc_itemCount` | `efak_medical_fnc_countItem [unit, class]` - loose plus usable kits |
| `ACME_fnc_itemTake` | `efak_medical_fnc_takeItem [unit, class]` - a loose one first, otherwise out of a kit |
| `ACME_fnc_itemList` | `efak_medical_fnc_listItems [unit, mode]` - ACE's list plus the kits' classes |

Portable oxygen: `ACM_breathing_fnc_useOxygenTankReserve` draws from a loose tank as before; with none
loose it calls `efak_medical_fnc_drawCharge [unit, "ACM_OxygenTank_425"]`, which draws one unit from a
tank inside a kit - the tank stays in the kit, opened - and answers the units left, `-1` when no kit
holds one. The NRB accepts a tank in a kit as its oxygen source through `ACME_fnc_itemCount`.

Nothing of this runs without EFAK: every EFAK call is behind `!isNil "efak_medical_fnc_..."`.
