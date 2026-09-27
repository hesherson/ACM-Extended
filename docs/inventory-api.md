# Medical supply compatibility API

ACM Extended 1.2.4 keeps ACE Shared Equipment as the authoritative source policy. Patient, medic and eligible vehicle
priority is resolved by `ACME_fnc_treatmentSupplyOrder`, counted by `ACME_fnc_treatmentSupplyCount`, and reserved by
`ACME_fnc_treatmentSupplyTake`.

For person inventories, compatibility-aware code uses three small primitives:

| Function | Arguments | Returns | No inventory mod |
|---|---|---|---|
| `ACME_fnc_itemCount` | `[unit, class]` | usable count | `ace_common_fnc_getCountOfItem` |
| `ACME_fnc_itemTake` | `[unit, class]` | one item taken | `removeItem` |
| `ACME_fnc_itemList` | `[unit, mode]` | available classes | `ace_common_fnc_uniqueItems` |

## Enhanced First Aid Kits

When Enhanced First Aid Kits exposes its public API, these primitives delegate to
`efak_medical_fnc_countItem`, `efak_medical_fnc_takeItem`, and `efak_medical_fnc_listItems`.
The 1.2.4 shared-treatment transaction layer also recognizes kit contents while preserving ACE's configured
patient/medic/vehicle source order. Vehicle cargo continues to use ACE/engine inventory handling.

If a reserved EFAK item is later refunded, ACME returns it to the exact donor unit as a loose inventory item. It is
not silently moved to a different patient, medic or vehicle.

Portable oxygen keeps its charge semantics: a loose tank is used first. If no loose tank exists and EFAK exposes
`efak_medical_fnc_drawCharge`, ACME may draw a charge from a tank inside a kit without removing the tank.

All EFAK calls are capability-gated with `isNil`; without EFAK loaded, the 1.2.4 native ACE/shared-equipment path is
unchanged.
