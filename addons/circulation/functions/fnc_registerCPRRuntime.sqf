#include "..\script_component.hpp"
if (isServer) then {
    GVAR(CPR_Sessions) = [];
    [QGVAR(cprTrack), {
        params ["_medic", "_patient", "_epoch"];
        if (isNull _medic || {isNull _patient}) exitWith {};
        // One server watchdog record per provider. A replacement episode makes every older record obsolete.
        GVAR(CPR_Sessions) = GVAR(CPR_Sessions) select {!((_x select 0) isEqualTo _medic)};
        GVAR(CPR_Sessions) pushBack [
            _medic, _patient, _epoch, owner _medic, CBA_missionTime,
            _medic getVariable [QGVAR(CPR_lastSeen), -100], CBA_missionTime
        ];
    }] call CBA_fnc_addEventHandler;
    [{
        private _keep = [];
        {
            _x params ["_medic", "_patient", "_epoch", "_owner", "_received", "_lastBeat", "_seenAt"];
            if (isNull _patient) then {[_medic, _patient, _epoch] call FUNC(cprRelease);};
            private _session = _patient getVariable [QGVAR(CPR_session), []];
            // Object variables and the tracking event can arrive in either order.
            if !(_session isEqualTo [_medic, _epoch]) then {
                if (!isNull _patient && {CBA_missionTime - _received < 3}) then {_keep pushBack _x;};
            } else {
                // CPR_lastSeen is a client clock value. Never subtract it from server mission time. A changed value
                // is only a heartbeat token; the dedicated server timestamps when it observes that change.
                private _beat = _medic getVariable [QGVAR(CPR_lastSeen), -100];
                if (_beat isNotEqualTo _lastBeat) then {
                    _x set [5, _beat];
                    _seenAt = CBA_missionTime;
                    _x set [6, _seenAt];
                };
                private _valid = [_medic, _patient] call FUNC(cprSessionValid);
                private _heartbeatExpired = CBA_missionTime - _seenAt >= 10;
                if (isNull _medic || {!alive _medic} || {owner _medic != _owner}
                    || {_heartbeatExpired}
                    || {!_valid && {CBA_missionTime - _received >= 3}}) then {
                    [_medic, _patient, _epoch] call FUNC(cprRelease);
                } else {_keep pushBack _x;};
            };
        } forEach GVAR(CPR_Sessions);
        GVAR(CPR_Sessions) = _keep;
    }, 1, []] call CBA_fnc_addPerFrameHandler;
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        {
            _x params ["_medic", "_patient", "_epoch"];
            if (_medic isEqualTo _unit) then {[_medic, _patient, _epoch] call FUNC(cprRelease);};
        } forEach GVAR(CPR_Sessions);
        false
    }];
};
if (hasInterface) then {
    // Player replacement includes respawn and remote control. Clean the captured old provider, not ACE_player.
    ["unit", {
        params ["_unit"];
        private _session = missionNamespace getVariable [QGVAR(CPR_LocalSession), []];
        if (_session isEqualTo [] || {(_session select 0) isEqualTo _unit}) exitWith {};
        _session call FUNC(cprCleanupLocal);
        if (!isNull _unit) then {_unit setVariable [QGVAR(isPerformingCPR), false, true];};
    }] call CBA_fnc_addPlayerEventHandler;
};
