/* Settle custody once, in the patient owner's unscheduled frame. Live Gear/treatment changes win.
   Never overwrite a replacement vest or restore spent supplies from a stale loadout snapshot. */
params ["_patient", "_saved", "_savedVar"];
if (isNull _patient || {!local _patient}) exitWith {false};
private _class = _saved param [0, "", [""]];
if (_class == "") exitWith {false};
if (_patient getVariable [_savedVar + "Settled", false]) exitWith {true};
private _live = _patient getVariable [_savedVar + "Live", false];
if (!_live) exitWith {
    // Compatibility for a saved pre-B218 episode which has no live holder at all.
    if (vest _patient != "") exitWith {true};
    // Pre-B218 saved only a vest loadout slot; do not rebuild the ENTIRE
    // casualty's loadout just to return one carrier. setUnitLoadout destroys
    // third-party uniform hidden selections (boots/gloves/sleeves/camo).
    _patient addVest _class;
    if (vest _patient != _class) exitWith {false};
    private _dest = vestContainer _patient;
    private _contents = _saved param [1, [], [[]]];
    {
        _x params [["_item", "", [""]], ["_count", 0, [0]]];
        if (_item == "" || {_count <= 0}) then {continue};
        if (isClass (configFile >> "CfgMagazines" >> _item)) then {
            private _ammo = _x param [2, getNumber (configFile >> "CfgMagazines" >> _item >> "count"), [0]];
            _dest addMagazineAmmoCargo [_item, _count, _ammo];
        } else {
            _dest addItemCargoGlobal [_item, _count];
        };
    } forEach _contents;
    // The old snapshot is inventory evidence, not a license to silently
    // drop items when a mod rejects cargo. Reject and retain it on mismatch.
    private _restored = true;
    {
        _x params [["_item", "", [""]], ["_count", 0, [0]]];
        if (_item == "" || {_count <= 0}) then {continue};
        private _seen = if (isClass (configFile >> "CfgMagazines" >> _item)) then {
            private _ammo = _x param [2, getNumber (configFile >> "CfgMagazines" >> _item >> "count"), [0]];
            {(_x select 0) == _item && {(_x select 1) == _ammo}}
                count (magazinesAmmoCargo _dest)
        } else {
            {_x == _item} count (itemCargo _dest)
        };
        if (_seen < _count) then {_restored = false;};
    } forEach _contents;
    if (!_restored) exitWith {
        removeVest _patient;
        diag_log "[ACME CARRIER B264] Legacy vest cargo restore rejected; original snapshot retained.";
        false
    };
    _patient setVariable [_savedVar + "Settled", true, true];
    true
};
// Do not discard either carrier when another mod equips a different vest during custody.
if (vest _patient != "") exitWith {false};
private _cargo = _patient getVariable ["ACME_carrierCargo", objNull];
if (!isNull _cargo && {(_cargo getVariable ["ACME_carrierSavedVar", ""]) != _savedVar
    || {!((_cargo getVariable ["ACME_carrierPatient", objNull]) isEqualTo _patient)}}) exitWith {false};
if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", true, true];};
private _snapshot = [_cargo] call ACME_fnc_carrierCargoSnapshot;
_patient addVest _class;
if (vest _patient != _class) exitWith {
    if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", false, true];};
    false
};
[vestContainer _patient, _snapshot] call ACME_fnc_carrierCargoPopulate;
if !([_snapshot, [vestContainer _patient] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual) exitWith {
    // Keep the live holder authoritative if the returned vest rejected any contents.
    removeVest _patient;
    if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", false, true];};
    diag_log "[ACME CARRIER] Restored cargo did not round-trip; live custody retained.";
    false
};
_patient setVariable ["ACME_carrierCargo", objNull, true];
_patient setVariable [_savedVar + "Live", false, true];
_patient setVariable [_savedVar + "Settled", true, true];
if (!isNull _cargo) then {
    // Pending supply refunds fall back to the donor once this exact container is gone.
    [_cargo, [[], [], [], []]] call ACME_fnc_carrierCargoPopulate;
    deleteVehicle _cargo;
};
true
