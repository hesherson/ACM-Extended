/* Resolve the inventory object that owns the currently selected Narc Box vial stock.
   B43 fail-safe: native ACM initializes the selector to Self, but a stale/invalid patient or vehicle
   selection must never turn the entire medication list into ghost 0.00 mL / x00 rows.  If the
   requested source no longer exists, fall back to the medic and normalize the selector to Self.
*/
params [['_medic', objNull, [objNull]], ['_selection', -1, [0]]];
if (isNull _medic) exitWith {objNull};
if (_selection < 0) then {
    _selection = missionNamespace getVariable ['ACM_circulation_SyringeDraw_InventorySelection', 0];
};

private _holder = switch (_selection) do {
    case 1: {
        private _target = missionNamespace getVariable ['ACM_circulation_SyringeDraw_Target', objNull];
        if (isNull _target) then {_target = uiNamespace getVariable ['ACME_SK_Patient',objNull];};
        _target
    };
    case 2: {objectParent _medic};
    default {_medic};
};

// A selected patient remains a valid source after death, but not after the provider walks away. Do not use alive as
// an inventory gate: that would both destroy corpse interaction and leak the patient's death state through the UI.
if (_selection == 1 && {!isNull _holder} && {_holder isNotEqualTo _medic}) then {
    private _sameVehicle = !isNull (objectParent _medic) && {(objectParent _medic) isEqualTo (objectParent _holder)};
    if (!_sameVehicle && {_medic distance _holder > 5}) then {_holder = objNull;};
    if (!isNull _holder && {!(_holder in ([_medic,_holder] call ACME_fnc_treatmentSupplyOrder))}) then {_holder = objNull;};
};

// Mirror ACM's own inventory-switch fail-safe. A genuinely stale patient/vehicle source is not a valid reason
// to make a medic's own carried vials disappear. A live shared source, however, must first be owner-leased; while
// that acknowledgement is pending we deliberately return objNull instead of silently debiting Self.
if (isNull _holder) then {
    _holder = _medic;
    if (_selection != 0) then {
        [ _medic ] call ACME_fnc_vialLeaseRelease;
        [[["syringeDrawInventorySelection", 0]]] call ACM_circulation_fnc_setLocalUiState;
    };
};
if (_selection in [1,2] && {_holder isNotEqualTo _medic}) exitWith {
    if ([_medic,_holder] call ACME_fnc_vialLeaseEnsure) then {_holder} else {objNull}
};

_holder
