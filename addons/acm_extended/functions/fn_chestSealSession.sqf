/* Low-frequency membership only. No server-wide cursor broadcast or per-cursor
   allPlayers scan. Snapshot and roster are sent to EVERY viewer of this patient. */
params ["_patient", "_viewer", "_mode", ["_token", ""]];
if (!isServer || {isNull _patient} || {isNull _viewer}) exitWith {};
private _key = netId _patient;
private _entry = ACME_CS_sessions getOrDefault [_key, [_patient, []]];
private _members = +(_entry select 1);
private _idx = _members findIf {(_x select 0) == _viewer};
private _changed = false;
private _oldToken = if (_idx < 0) then {""} else {(_members select _idx) param [2, ""]};
// A heartbeat renews its enrolled episode only. Delayed packets cannot resurrect a
// closed viewer or overwrite the token of a newer entry from the same provider.
if (_mode == "ping" && {_idx < 0 || {_token != _oldToken}}) exitWith {};
if (_mode == "leave" && {_token != ""} && {_token != _oldToken}) exitWith {};
if (_token == "") then {_token = _oldToken;};
switch (_mode) do {
    case "join";
    case "ping";
    case "sync": {
        if (_idx < 0) then { _members pushBack [_viewer, CBA_missionTime, _token]; _changed = true; }
        else { _members set [_idx, [_viewer, CBA_missionTime, _token]]; };
    };
    case "leave": {
        if (_idx >= 0) then { _members deleteAt _idx; _changed = true; };
        if (_token != "") then {[_patient, "chestSealPatientEnd", [_patient, _token]] call ACME_fnc_ownerDispatch;};
    };
};
if (count _members == 0) then { ACME_CS_sessions deleteAt _key; }
else { ACME_CS_sessions set [_key, [_patient, _members]]; };
private _viewers = _members apply {_x select 0};
if (_changed && {count _viewers > 0}) then {
    ["ACME_CS_roster", [_patient, _viewers], _viewers] call CBA_fnc_targetEvent;
};
if (_mode in ["join", "sync"] || {_changed && {_mode == "ping"}}) then {
    // Random positions are generated once by the stable authority, never per provider.
    [_patient] call ACME_fnc_chestSealGenHoles;
    ["ACME_CS_snapshot", [_patient, _patient getVariable ["ACME_CS_netSnapshot", []]], _viewer] call CBA_fnc_targetEvent;
};
