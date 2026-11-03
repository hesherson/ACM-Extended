params ["_o", "_energy", "_sync", ["_ptype", "Adult"]];
if (isNull _o || {!(_o getVariable ["acme_tempusls_armed", false])}) exitWith {};
private _pat = _o getVariable ["acme_tempusls_pat", objNull];
private _medic = call ACME_fnc_controlledProvider;
if (isNull _pat || {isNull _medic}) exitWith {};
private _seq = (missionNamespace getVariable ["ACME_tempusls_seq", 0]) + 1;
missionNamespace setVariable ["ACME_tempusls_seq", _seq];
private _id = format ["tls:%1:%2:%3", clientOwner, _seq, netId _o];
[_o, _medic, _pat, _energy, _sync, _ptype, _id, [_pat] call ACME_fnc_clinicalEpoch, serverTime]
    remoteExecCall ["ACME_fnc_tempusLsShock", _pat];
