/* Owner-local reconciliation of ACME's one composable ACE visibility reason.
 * state: recompute; retire: local bookkeeping only; reset/fired: retire this awake lying episode.
 * restore: validated deserialization has finished; clear only ACME reset/firing latches and recompute.
 * Existing ACE/other reasons are never cleared. No raw camouflage, side, captive or physics changes.
 */
params [["_unit", objNull, [objNull]], ["_mode", "state", [""]]];
if (canSuspend) exitWith {isNil {[_unit, _mode] call ACME_fnc_aiProtectionSync;};};
private _candidates = missionNamespace getVariable ["ACME_aiProtection_candidates", []];
private _retire = {
    _candidates = _candidates - [_unit];
    missionNamespace setVariable ["ACME_aiProtection_candidates", _candidates];
    if (!isNull _unit) then {
        private _handlers = _unit getVariable ["ACME_aiProtection_handlers", []];
        if ((_handlers param [0, -1]) >= 0) then {_unit removeEventHandler ["AnimChanged", _handlers select 0];};
        if ((_handlers param [1, -1]) >= 0) then {_unit removeEventHandler ["FiredMan", _handlers select 1];};
        _unit setVariable ["ACME_aiProtection_handlers", [], false];
        _unit setVariable ["ACME_aiProtection_localEpoch", [], false];
    };
};
if (isNull _unit || {_mode == "retire"} || {!local _unit}) exitWith {call _retire;};
if (_mode == "restore" && {_unit getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

private _unconscious = _unit getVariable ["ACE_isUnconscious", false];
private _lying = _unit getVariable ["ACM_core_Lying_State", false];
if !(_lying isEqualType true) then {_lying = _lying isEqualType 0 && {_lying > 0};};
private _lastUnconscious = _unit getVariable ["ACME_aiProtection_lastUnconscious", false];
private _blocked = _unit getVariable ["ACME_aiProtection_awakeBlocked", false];
private _resetPending = _unit getVariable ["ACME_aiProtection_resetPending", false];
// Full-heal begins before ACE clears the old unconscious flag. Do not immediately re-add the reason from
// that stale flag; wait until its false transition has actually been observed. ACE's own reason remains intact.
if (!_unconscious) then {_resetPending = false;};
if (_mode == "reset") then {_resetPending = _unconscious;};
if (_mode == "restore") then {_resetPending = false;};
if (_resetPending isNotEqualTo (_unit getVariable ["ACME_aiProtection_resetPending", false])) then {
    _unit setVariable ["ACME_aiProtection_resetPending", _resetPending, true];
};
if (!_lying || {_unconscious && {!_lastUnconscious} && {!_resetPending}}) then {_blocked = false;};
if (_mode in ["reset", "fired"]) then {_blocked = _lying;};
if (_mode == "restore") then {_blocked = false;};
if (_blocked isNotEqualTo (_unit getVariable ["ACME_aiProtection_awakeBlocked", false])) then {
    // This episode latch follows the patient across ownership changes; handler IDs and replay clocks do not.
    _unit setVariable ["ACME_aiProtection_awakeBlocked", _blocked, true];
};
_unit setVariable ["ACME_aiProtection_lastUnconscious", _unconscious, false];

private _reason = "acme_medical_downed";
private _reasons = missionNamespace getVariable ["ace_common_statusEffects_setHidden", []];
private _ready = (missionNamespace getVariable ["ace_common_settingsInitFinished", false])
    && {_reason in _reasons} && {!isNil "ace_common_fnc_statusEffect_get"}
    && {!isNil "ace_common_fnc_statusEffect_set"} && {!isNil "ace_common_fnc_statusEffect_sendEffects"};
private _ours = false;
private _aggregate = false;
private _activeReasons = [];
if (_ready) then {
    private _effect = [_unit, "setHidden"] call ace_common_fnc_statusEffect_get;
    _activeReasons = _effect param [1, []];
    _ours = _reason in _activeReasons;
    _aggregate = !(_activeReasons isEqualTo []);
};
private _wanted = _mode != "reset" && {[_unit] call ACME_fnc_aiProtectionWanted};
private _relevant = alive _unit && {_unconscious || {_lying}};
// An owner acquiring a patient before the reason table arrives must not abandon a possibly inherited reason.
private _unknownEffect = !_ready && {(_unit getVariable ["ace_common_effect_setHidden", -1]) >= 0};
if (!_relevant && {!_ours} && {!_unknownEffect}) exitWith {call _retire;};

if (_relevant) then {
    _candidates pushBackUnique _unit;
    missionNamespace setVariable ["ACME_aiProtection_candidates", _candidates];
    private _handlers = _unit getVariable ["ACME_aiProtection_handlers", []];
    if (_handlers isEqualTo []) then {
        private _animation = _unit addEventHandler ["AnimChanged", {
            params ["_unit"];
            [_unit] call ACME_fnc_aiProtectionSync;
        }];
        private _fired = _unit addEventHandler ["FiredMan", {
            params ["_unit"];
            [_unit, "fired"] call ACME_fnc_aiProtectionSync;
        }];
        _unit setVariable ["ACME_aiProtection_handlers", [_animation, _fired], false];
    };
} else {
    _candidates pushBackUnique _unit;
    missionNamespace setVariable ["ACME_aiProtection_candidates", _candidates];
};
if (!_ready) exitWith {};

private _changed = _wanted isNotEqualTo _ours;
if (_changed) then {[_unit, "setHidden", _reason, _wanted] call ace_common_fnc_statusEffect_set;};

private _epoch = [clientOwner, _unit getVariable ["ACME_providerLocalityEpoch", 0]];
private _newOwner = !((_unit getVariable ["ACME_aiProtection_localEpoch", []]) isEqualTo _epoch);
private _serial = missionNamespace getVariable ["ACME_aiProtection_replaySerial", 0];
private _newObserver = (_unit getVariable ["ACME_aiProtection_replaySerial", -1]) != _serial;
private _lastReplay = _unit getVariable ["ACME_aiProtection_lastReplay", -100];
private _now = diag_tickTime;
private _overwritten = _wanted && {([_unit getUnitTrait "camouflageCoef"] param [0, 1]) > 0};
// ACE automatically emits on aggregate 0<->nonzero transitions. Adding our reason alongside ACE unconsciousness
// does not emit, so explicitly repair that entry once. Coalesce observer joins and external trait overwrites.
private _automaticSend = _changed && {(!_aggregate && {_wanted}) || {!_wanted && {count _activeReasons == 1}}};
if (_automaticSend) then {
    _lastReplay = _now;
    _unit setVariable ["ACME_aiProtection_lastReplay", _now, false];
    _unit setVariable ["ACME_aiProtection_replaySerial", _serial, false];
};
private _replay = _wanted && {!_automaticSend}
    && {_newOwner || {_changed} || {(_newObserver || {_overwritten}) && {_now - _lastReplay >= 5}}};
if (_replay) then {
    [_unit, "setHidden"] call ace_common_fnc_statusEffect_sendEffects;
    _unit setVariable ["ACME_aiProtection_lastReplay", _now, false];
    _unit setVariable ["ACME_aiProtection_replaySerial", _serial, false];
};
_unit setVariable ["ACME_aiProtection_localEpoch", _epoch, false];
if (!_relevant) then {call _retire;};
