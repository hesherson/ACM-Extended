/* Per-patient/provider chest-seal log dedupe.
 * Multiple wounds treated during one short working sequence should read as one action in the activity log.
 * Apply, surgical burp and remove retain independent cooldown keys. Ordinary panel burps use their session.
 */
params ["_patient", ["_action", "", [""]], ["_message", "", [""]], ["_args", [], [[]]], ["_medic", objNull], ["_cooldown", -1, [0]], ["_session", "", [""]]];
if (isNull _patient || {_action == ""} || {_message == ""}) exitWith {false};

// B216: one observation for the whole open traumatic-seal panel, including multiple wounds.
// The patient owner publishes this receipt so a locality handoff cannot duplicate the quick-view entry.
// Clinical treatment remains repeatable; only its presentation is deduplicated here.
if (toLowerANSI _action == "burp" && {_session != ""}) exitWith {
    private _active = _patient getVariable ["ACME_CS_ProcedureTokens", []];
    if (!local _patient || {!(_session in _active)}) exitWith {false};
    private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
    private _record = _patient getVariable ["ACME_CS_burpLogSessions", [-1, []]];
    private _logged = if ((_record param [0, -1]) == _epoch) then {+(_record param [1, []])} else {[]};
    _logged = _logged select {_x in _active};
    if (_session in _logged) exitWith {false};
    _logged pushBack _session;
    _patient setVariable ["ACME_CS_burpLogSessions", [_epoch, _logged], true];
    [_patient, "quick_view", _message, _args] call ace_medical_treatment_fnc_addToLog;
    true
};

if (_cooldown < 0) then {
    _cooldown = switch (toLowerANSI _action) do {
        case "apply": {missionNamespace getVariable ["ACME_chestSealApplyLogCooldown", 30]};
        case "burp": {missionNamespace getVariable ["ACME_chestSealBurpLogCooldown", 10]};
        case "remove": {missionNamespace getVariable ["ACME_chestSealRemoveLogCooldown", 10]};
        default {10};
    };
};

private _who = if (isNull _medic) then {"none"} else {netId _medic};
private _key = format ["%1:%2", toLowerANSI _action, _who];
private _times = _patient getVariable ["ACME_chestSealActivityLogTimes", createHashMap];
private _now = serverTime;
if ((_now - (_times getOrDefault [_key, -1e6])) < _cooldown) exitWith {false};
_times set [_key, _now];
_patient setVariable ["ACME_chestSealActivityLogTimes", _times, true];

[_patient, "activity", _message, _args] call ace_medical_treatment_fnc_addToLog;
true
