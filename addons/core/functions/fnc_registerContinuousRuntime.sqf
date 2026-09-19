#include "..\script_component.hpp"
// Server watchdog for manual holds that can otherwise survive the provider's death/disconnect.
// A dead patient remains treatable; only a lost provider or invalid context releases the hold.
if (!isServer) exitWith {};
GVAR(ContinuousHolds) = [];
[QGVAR(continuousHoldTrack), {
    params ["_medic", "_patient", "_epoch", "_state"];
    if (isNull _medic || {isNull _patient}
        || {!(_state in ["ACM_airway_HeadTilt_State", "ACM_core_CarryAssist_State"])}) exitWith {};
    GVAR(ContinuousHolds) pushBackUnique [_medic, _patient, _epoch, _state, owner _medic, CBA_missionTime, -1, CBA_missionTime];
}] call CBA_fnc_addEventHandler;
[{
    private _keep = [];
    {
        _x params ["_medic", "_patient", "_epoch", "_state", "_owner", "_received", "_lastBeat", "_seenAt"];
        private _matches = (_patient getVariable [_state + "_Session", []]) isEqualTo [_medic, _epoch];
        private _grace = CBA_missionTime - _received < 3;
        if (!_matches) then {
            if (_grace && {!isNull _patient}) then {_keep pushBack _x;};
        } else {
            // Receive-time expiry avoids comparing a client's mission clock with the server clock.
            private _beat = _medic getVariable [QGVAR(ContinuousAction_LastSeen), -100];
            if (_beat isNotEqualTo _lastBeat) then {
                _x set [6, _beat];
                _x set [7, CBA_missionTime];
                _seenAt = CBA_missionTime;
            };
            private _valid = !isNull _medic && {alive _medic}
                && {!(_medic getVariable ["ACE_isUnconscious", false])}
                && {owner _medic == _owner}
                && {(_medic getVariable [QGVAR(ContinuousAction_Session), []]) isEqualTo [_patient, _epoch]}
                && {CBA_missionTime - _seenAt < 10}
                && {objectParent _medic isEqualTo objectParent _patient}
                && {(_medic distance _patient) <= ACEGVAR(medical_gui,maxDistance)};
            if (_valid || {_grace && {alive _medic}}) then {_keep pushBack _x;} else {
                [_medic, _patient, _epoch, _state] call FUNC(continuousHoldRelease);
            };
        };
    } forEach GVAR(ContinuousHolds);
    GVAR(ContinuousHolds) = _keep;
}, 1, []] call CBA_fnc_addPerFrameHandler;
addMissionEventHandler ["HandleDisconnect", {
    params ["_unit"];
    {
        _x params ["_medic", "_patient", "_epoch", "_state"];
        if (_unit isEqualTo _medic) then {[_medic, _patient, _epoch, _state] call FUNC(continuousHoldRelease);};
    } forEach GVAR(ContinuousHolds);
    false
}];
