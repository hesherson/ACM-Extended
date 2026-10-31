/* Native success/failure passes its captured capillary serial. Never stop a successor's hold. */
params ["_args", ["_success", false, [false]]];
_args params ["_medic", "_patient", "_part"];
private _serial = _args param [7, -1];
if (isNull _medic || {!local _medic} || {_serial < 0}) exitWith {};
private _entry = _medic getVariable ["ACME_capillaryPose", []];
if ((_entry param [0, -2]) != _serial || {(_entry param [1, objNull]) isNotEqualTo _patient}) exitWith {};
_medic setVariable ["ACME_capillaryPose", [], false];
private _pose = _entry param [2, -1];
if (_pose >= 0) then {[_medic, "pulse", _pose] call ACME_fnc_treatmentPoseStop;};
if (_success && {!isNull _patient} && {alive _medic} && {[_medic] call ace_common_fnc_isAwake}) then {
    [_medic, _patient, _part] call ACM_circulation_fnc_checkCapillaryRefill;
};
