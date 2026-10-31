/* Settle custody once, in the patient owner's unscheduled frame. Live Gear/treatment changes win.
   Never overwrite a replacement vest or restore spent supplies from a stale loadout snapshot. */
params ["_patient", "_saved", "_savedVar"];
if (isNull _patient || {!local _patient}) exitWith {false};
// B267: an intentionally applied kit outranks the previous carrier snapshot.
// A retired slot stays explicitly empty, so late pre-boundary callers cannot
// treat missing live cargo as permission to recreate old equipment.
private _current = _patient getVariable [_savedVar, _saved];
if (_current isNotEqualTo _saved) exitWith {false};
private _kit = _patient getVariable ["ACME_equipmentKitEpoch", 0];
if ((_patient getVariable [_savedVar + "KitEpoch", _kit]) != _kit) exitWith {false};
private _class = _saved param [0, "", [""]];
if (_class == "") exitWith {false};
if (_patient getVariable [_savedVar + "Settled", false]) exitWith {true};
private _live = _patient getVariable [_savedVar + "Live", false];
if (!_live) exitWith {
    // B265: decode the OLD vest-only loadout before touching equipment. Modern
    // custody below uses live cargo, never this historical snapshot.
    if (vest _patient != "") exitWith {false};
    if !(_saved isEqualType [] && {count _saved == 2} && {(_saved select 1) isEqualType []}) exitWith {false};
    ([_saved] call ACM_core_fnc_carrierLegacySnapshot) params ["_valid", "_snapshot"];
    if (!_valid) exitWith {false};
    _patient addVest _class;
    if (vest _patient != _class) exitWith {false};
    [vestContainer _patient, _snapshot] call ACME_fnc_carrierCargoPopulate;
    if !([_snapshot, [vestContainer _patient] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual) exitWith {
        removeVest _patient;
        diag_log "[ACME CARRIER B265] Legacy cargo rejected; original snapshot retained.";
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
