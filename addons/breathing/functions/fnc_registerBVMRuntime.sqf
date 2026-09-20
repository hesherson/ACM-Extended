#include "..\script_component.hpp"
if (isServer) then {
    GVAR(BVM_Sessions) = [];
    [QGVAR(bvmTrack), {
        params ["_medic", "_patient", "_epoch"];
        if (isNull _medic || {isNull _patient}) exitWith {};
        GVAR(BVM_Sessions) pushBackUnique [_medic, _patient, _epoch, owner _medic,
            CBA_missionTime, _medic getVariable [QGVAR(BVM_lastSeen), -100], CBA_missionTime];
    }] call CBA_fnc_addEventHandler;
    [{
        private _keep = [];
        {
            _x params ["_medic", "_patient", "_epoch", "_owner", "_received", "_lastBeat", "_seenAt"];
            if (isNull _patient) then {[_medic, _patient, _epoch] call FUNC(bvmRelease);};
            private _session = _patient getVariable [QGVAR(BVM_session), []];
            // Object variables and the tracking event can arrive in either order.
            if !(_session isEqualTo [_medic, _epoch]) then {
                if (!isNull _patient && {CBA_missionTime - _received < 3}) then {_keep pushBack _x;};
            } else {
                // Client mission time may differ from server time. A changed heartbeat
                // proves activity; measure its age on this server after receiving it.
                private _beat = _medic getVariable [QGVAR(BVM_lastSeen), -100];
                if (_beat isNotEqualTo _lastBeat) then {
                    _x set [5, _beat];
                    _x set [6, CBA_missionTime];
                    _seenAt = CBA_missionTime;
                };
                private _valid = ([_medic, _patient] call FUNC(bvmSessionValid))
                    && {CBA_missionTime - _seenAt < 10};
                if (isNull _medic || {!alive _medic} || {owner _medic != _owner}
                    || {!_valid && {CBA_missionTime - _received >= 3}}) then {
                    [_medic, _patient, _epoch] call FUNC(bvmRelease);
                } else {_keep pushBack _x;};
            };
        } forEach GVAR(BVM_Sessions);
        GVAR(BVM_Sessions) = _keep;
    }, 1, []] call CBA_fnc_addPerFrameHandler;
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        {
            _x params ["_medic", "_patient", "_epoch"];
            if (_medic isEqualTo _unit) then {[_medic, _patient, _epoch] call FUNC(bvmRelease);};
        } forEach GVAR(BVM_Sessions);
        false
    }];
};
if (hasInterface) then {
    // Player replacement includes respawn and remote control. Clean the captured old provider, not ACE_player.
    ["unit", {
        params ["_unit"];
        private _session = missionNamespace getVariable [QGVAR(BVM_LocalSession), []];
        if (_session isEqualTo [] || {(_session select 0) isEqualTo _unit}) exitWith {};
        _session call FUNC(bvmCleanupLocal);
        if (!isNull _unit) then {_unit setVariable [QGVAR(isUsingBVM), false, true];};
    }] call CBA_fnc_addPlayerEventHandler;
};
