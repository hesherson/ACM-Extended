/*
 * Phase 58: authoritative HPMK state transition writer.
 * ACME_hpmk_state and ACME_hpmk_on are one contract: only wrapped/exposed states actively rewarm.
 * The publication switches preserve legacy direct-vs-setVarNet behavior where required.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_state", "", [""]],
    ["_public", true, [true]],
    ["_deduplicate", false, [true]]
];
if (isNull _patient) exitWith {_state};
if !(_state in ["", "prepped", "wrapped", "exposed"]) exitWith {_patient getVariable ["ACME_hpmk_state", ""]};
if (!local _patient) exitWith {
    [_patient, "hpmkState", [_patient, _state, _public, _deduplicate]] call ACME_fnc_ownerDispatch;
    _state
};
private _on = _state in ["wrapped", "exposed"];
// Server safety/visual maintenance tracks only casualties that actually carry HPMK state. This replaces the old
// perpetual allUnits scan.
["ACME_hpmkServerTrack", [_patient, _state]] call CBA_fnc_serverEvent;
if (_public && {_deduplicate}) then {
    [_patient, "ACME_hpmk_state", _state] call ACME_fnc_setVarNet;
    [_patient, "ACME_hpmk_on", _on] call ACME_fnc_setVarNet;
} else {
    _patient setVariable ["ACME_hpmk_state", _state, _public];
    _patient setVariable ["ACME_hpmk_on", _on, _public];
};
// what he wears and how he lies follow the state
[_patient] call ACME_fnc_hpmkDress;
_state
