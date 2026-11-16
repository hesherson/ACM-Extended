/*
 * Where the casualty is local: attach them to whatever the SKED is attached to now (dragger, lead rescuer),
 * at the same place relative to the SKED, or onto the SKED itself if it is free. The root is read when this
 * runs, so a late call can never leave a chain of attachments.
 * Arguments: 0: casualty, 1: SKED (anything after is ignored).
 */
params ["_patient", "_litter"];
if (!local _patient || {isNull _litter}) exitWith {};
if !((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter) exitWith {};
(_litter getVariable ["acme_sked_attach", []]) params [["_off", []], ["_dir", [0, 1, 0]], ["_up", [0, 0, 1]]];
if (_off isEqualTo []) exitWith {};
private _root = attachedTo _litter;
if (isNull _root) exitWith {
    _patient attachTo [_litter, _off];
    _patient setVectorDirAndUp [_dir, _up];
};
private _offR = _root worldToModelVisual (_litter modelToWorldVisual _off);
private _dirR = _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _dir);
private _upR = _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _up);
_patient attachTo [_root, _offR];
_patient setVectorDirAndUp [_dirR, _upR];
