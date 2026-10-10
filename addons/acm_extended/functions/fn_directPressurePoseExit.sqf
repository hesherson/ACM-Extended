/* B213: finite, preemptible empty-hands exit for movement or explicit cancellation.
 * It owns only presentation. The pressure claim survives movement; Stop releases the claim before entering here.
 * A successor treatment wins without a neutral pose, speed reset, delayed retry or old held worker fighting it.
 */
params ["_medic", ["_prone", false]];
if (isNull _medic || {!local _medic} || {_medic getVariable ["ACE_isUnconscious", false]} || {!([_medic] call ace_common_fnc_isAwake)} || {!alive _medic} || {[_medic] call ACME_fnc_animBlocked}
    || {[_medic, _medic getVariable ["ACME_DP_Patient", objNull]] call ACME_fnc_directPressurePoseBusy}) exitWith {false};
if ((_medic getVariable ["ACME_DP_Exit", []]) isNotEqualTo []) exitWith {true};
private _neutral = [_medic, "AmovPknlMstpSnonWnonDnon", _prone] call ACME_fnc_providerAnimation;
_medic setUnitPos "AUTO";
// There is no authored prone medicEnd. Retain prone rather than lifting the provider into the kneeling RTM.
if (_neutral == "AmovPpneMstpSnonWnonDnon") exitWith {[_medic, _neutral, 1] call ACME_fnc_doAnim; true};
private _anim = "AinvPknlMstpSnonWnonDnon_medicEnd";
private _nativeSpeed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _anim >> "speed");
private _duration = if (_nativeSpeed < 0) then {-_nativeSpeed} else {if (_nativeSpeed > 0) then {1 / _nativeSpeed} else {2}};
private _serial = (_medic getVariable ["ACME_DP_ExitSerial", 0]) + 1;
_medic setVariable ["ACME_DP_ExitSerial", _serial, false];
private _priorRate = 1; // Never capture a previous medical acceleration as the walking baseline.
if !([_medic] call ACME_fnc_providerAnimSpeedOwned) then {_medic setAnimSpeedCoef 1;};
private _state = [_serial, _medic getVariable ["ACME_DP_PoseToken", 0],
    _medic getVariable ["ACME_providerLocalityEpoch", 0], _medic getVariable ["ACME_treatmentPoseEpoch", 0],
    CBA_missionTime, -1, (_duration / 1.5) min 8, _priorRate, _anim, _neutral];
_medic setVariable ["ACME_DP_Exit", _state, false];
private _episode = [serverTime, _serial, clientOwner];
_state pushBack _episode;
_medic setVariable ["ACME_DP_ExitEpisode", _episode + [true], true];
["ACME_directPressurePoseExitSync", [_medic, _episode, _state select 3, _state select 6, true]] call CBA_fnc_globalEvent;
// Speed is applied only once the actual exit RTM is observed below.
[_medic, _anim, 1] call ACME_fnc_doAnim;
[{
    params ["_args", "_pfh"];
    _args params ["_m", "_state"];
    _state params ["_serial", "_token", "_locality", "_poseEpoch", "_started", "_seen", "_duration", "_priorRate", "_anim", "_neutral", "_episode"];
    if (isNull _m || {!local _m} || {(_m getVariable ["ACME_providerLocalityEpoch", 0]) != _locality}) exitWith {
        if (!isNull _m) then {
            if (((_m getVariable ["ACME_DP_Exit", []]) param [0, -1]) == _serial) then {_m setVariable ["ACME_DP_Exit", [], false];};
            [_m, _serial] call ACME_fnc_directPressureExitSpeedRelease;
        };
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    if (((_m getVariable ["ACME_DP_Exit", []]) param [0, -1]) != _serial) exitWith {
        [_m, _serial] call ACME_fnc_directPressureExitSpeedRelease;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _successor = (_m getVariable ["ACME_DP_PoseToken", 0]) != _token
        || {(_m getVariable ["ACME_treatmentPoseEpoch", 0]) != _poseEpoch}
        || {[_m, _m getVariable ["ACME_DP_Patient", objNull]] call ACME_fnc_directPressurePoseBusy};
    private _unavailable = !alive _m || {_m getVariable ["ACE_isUnconscious", false]} || {!([_m] call ace_common_fnc_isAwake)} || {!isNull objectParent _m};
    private _current = toLowerANSI animationState _m;
    private _inExit = _current == toLowerANSI _anim;
    if (_seen < 0 && {_inExit}) then {_seen = CBA_missionTime; _state set [5, _seen];};
    // Animate Rewrite resets its walking rate on the first non-walk state. Reassert only during our observed RTM.
    if (_inExit && {!_successor} && {!_unavailable}) then {
        _m setVariable ["ACME_DP_ExitSpeedOwner", _serial, false];
        if (abs ((getAnimSpeedCoef _m) - 1.5) > 0.01) then {_m setAnimSpeedCoef 1.5;};
    };
    private _complete = (CBA_missionTime - _seen) >= _duration;
    if (_inExit) then {
        private _nativeDuration = _m getUnitMovesInfo 2;
        private _nativeElapsed = _m getUnitMovesInfo 1;
        if (_nativeDuration isEqualType 0 && {finite _nativeDuration} && {_nativeDuration > 0}
            && {_nativeElapsed isEqualType 0} && {finite _nativeElapsed} && {_nativeElapsed >= 0}) then {
            _duration = (_nativeDuration / 1.5) min 8;
            _state set [6, _duration];
            _complete = _nativeElapsed >= (_nativeDuration - 0.025);
        };
    };
    private _finished = (_seen >= 0 && {!_inExit || {_complete}})
        || {(_seen < 0) && {(CBA_missionTime - _started) >= 1.5}}
        || {(CBA_missionTime - _started) > _duration + 2};
    if (_successor || {_unavailable} || {_finished}) exitWith {
        _m setVariable ["ACME_DP_Exit", [], false];
        if ((_m getVariable ["ACME_DP_ExitEpisode", []]) isEqualTo (_episode + [true])) then {
            _m setVariable ["ACME_DP_ExitEpisode", _episode + [false], true];
            ["ACME_directPressurePoseExitSync", [_m, _episode, _poseEpoch, _duration, false]] call CBA_fnc_globalEvent;
        };
        [_pfh] call CBA_fnc_removePerFrameHandler;
        if (!_successor && {!_unavailable}) then {
            // Leave freely chosen movement alone. Only finish a still-visible exit/old hold into empty-hands idle.
            if (_inExit || {_current == "acme_directpressurehold"}) then {[_m, [_m, _neutral] call ACME_fnc_providerAnimation, 1] call ACME_fnc_doAnim;};
        };
        [_m, _serial] call ACME_fnc_directPressureExitSpeedRelease;
    };
}, 0, [_medic, _state]] call CBA_fnc_addPerFrameHandler;
true
