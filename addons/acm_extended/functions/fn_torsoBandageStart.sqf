/* B226: native treatment owns the timer/clinical outcome; this owner covers presentation only. */
params ["_medic", "_patient", "_part", "_class", ["_duration", 15, [0]]];
if (isNull _medic || {!local _medic} || {!alive _medic} || {!isNull objectParent _medic}) exitWith {-1};
private _serial = (_medic getVariable ["ACME_torsoBandageSerial", 0]) + 1;
_medic setVariable ["ACME_torsoBandageSerial", _serial, false];
private _visible = toLowerANSI animationState _medic;
private _emptyHandoff = _visible in ["acm_genericcontinuous","acme_junctionalwork","acme_chestsealworkspace","acme_directpressurehold"];
private _epoch = [_medic, "torsoBandage", -1, _patient, _emptyHandoff] call ACME_fnc_treatmentPoseStart;
_medic setVariable ["ACME_torsoBandage", [_serial, _patient, _part, _class, _epoch], false];
// Finite orphan fallback if a progress display is destroyed without either native completion.
// The serial plus pose epoch protect any successor; failure never plays a placement motion.
private _bound = if (finite _duration && {_duration >= 0}) then {_duration + 5} else {20};
[{
    params ["_medic", "_patient", "_part", "_class", "_serial"];
    [[_medic, _patient, _part, _class, objNull, "", false, _serial], false] call ACME_fnc_torsoBandageFinish;
}, [_medic, _patient, _part, _class, _serial], _bound] call CBA_fnc_waitAndExecute;
_serial
