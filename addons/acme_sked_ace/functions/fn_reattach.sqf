/*
 * Where the casualty is local: attach them to whatever the SKED is attached to now (dragger, lead rescuer),
 * at the same place relative to the SKED, or onto the SKED itself if it is free. The root is read when this
 * runs, so a late call can never leave a chain of attachments.
 * Arguments: 0: casualty, 1: SKED, 2: do not write it to the log <BOOL> (default: false).
 */
params ["_patient", "_litter", ["_quiet", false, [false]]];
if (!local _patient || {isNull _litter} || {!isNull objectParent _patient}
    || {_patient getVariable ["acme_sked_loading", false]}) exitWith {};
if !((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter) exitWith {};
(_litter getVariable ["acme_sked_attach", []]) params [["_off", []], ["_dir", [0, 1, 0]], ["_up", [0, 0, 1]]];
if (_off isEqualTo []) exitWith {};
private _root = [_litter] call acme_sked_fnc_patientRoot;
// (the pose guard sends the turn again every few seconds: that is not written to the log)
if (!_quiet) then {["patient reattach", _litter, _patient, [attachedTo _patient, _root]] call acme_sked_fnc_traceTransport;};
if (_root isEqualTo _litter) exitWith {
    _patient attachTo [_litter, _off];
    _patient setVectorDirAndUp [_dir, _up];
};
private _offR = _root worldToModelVisual (_litter modelToWorldVisual _off);
private _dirR = _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _dir);
private _upR = _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _up);
_patient attachTo [_root, _offR];
_patient setVectorDirAndUp [_dirR, _upR];
