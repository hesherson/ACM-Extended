params ["_medic", "_patient", "_epoch", "_id", ["_hops", 0]];
if (isNull _patient || {isNull _medic} || {!(_id isEqualType "")} || {_id == ""} || {count _id > 128}
    || {!(_hops isEqualType 0)} || {!finite _hops} || {_hops != floor _hops} || {_hops < 0} || {_hops > 4}) exitWith {false};
if (!local _patient) exitWith {
    if (_hops < 4) then {["LNX_DD1380_DocumentRequest", [_medic, _patient, _epoch, _id, _hops + 1], _patient] call CBA_fnc_targetEvent;};
    false
};
private _sameVehicle = !isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient};
private _allowed = alive _medic && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {_sameVehicle || {_medic distance _patient <= 6}}
    && {_epoch isEqualType 0} && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)};
private _document = if (_allowed) then {[_patient, true] call DD1380_card_fnc_getDocument} else {[]};
["LNX_DD1380_OpenReady", [_medic, _patient, _epoch, _id, _document], _medic] call CBA_fnc_targetEvent;
_allowed
