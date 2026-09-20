#include "..\script_component.hpp"
if (isServer) then {
    // Keep only a cleanup reference for each provider. ACM's local action owns the
    // running BVM; no server timer or replicated heartbeat may stop live breaths.
    GVAR(BVM_Sessions) = [];
    [QGVAR(bvmTrack), {
        params ["_medic", "_patient", "_epoch"];
        if (isNull _medic || {isNull _patient}) exitWith {};
        GVAR(BVM_Sessions) = GVAR(BVM_Sessions) select {!((_x select 0) isEqualTo _medic)};
        GVAR(BVM_Sessions) pushBack [_medic, _patient, _epoch];
    }] call CBA_fnc_addEventHandler;

    addMissionEventHandler ["EntityKilled", {
        params ["_unit"];
        {
            _x params ["_medic", "_patient", "_epoch"];
            if (_medic isEqualTo _unit) then {[_medic, _patient, _epoch] call FUNC(bvmRelease);};
        } forEach GVAR(BVM_Sessions);
        GVAR(BVM_Sessions) = GVAR(BVM_Sessions) select {!((_x select 0) isEqualTo _unit)};
    }];
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        {
            _x params ["_medic", "_patient", "_epoch"];
            if (_medic isEqualTo _unit) then {[_medic, _patient, _epoch] call FUNC(bvmRelease);};
        } forEach GVAR(BVM_Sessions);
        GVAR(BVM_Sessions) = GVAR(BVM_Sessions) select {!((_x select 0) isEqualTo _unit)};
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
