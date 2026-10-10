#include "..\script_component.hpp"
if (isServer) then {
    // Keep one cleanup reference per provider. ACM's local action owns running BVM.
    // Paused/live sessions have no heartbeat timeout: only actual provider loss or
    // a change of owner can retire the captured episode.
    GVAR(BVM_Sessions) = [];
    [QGVAR(bvmTrack), {
        params ["_medic", "_patient", "_epoch"];
        if (isNull _medic || {isNull _patient}) exitWith {};
        GVAR(BVM_Sessions) = GVAR(BVM_Sessions) select {!((_x select 0) isEqualTo _medic)};
        // B254: remember the owner which created this BVM episode on the server.
        // A headless-client/player locality change must not preserve an old lease.
        GVAR(BVM_Sessions) pushBack [_medic, _patient, _epoch, owner _medic, CBA_missionTime];
    }] call CBA_fnc_addEventHandler;

    // Scan only BVM's tracked sessions. Do not expire paused BVM by time or
    // heartbeat age: the server clock only bounds out-of-order track/session
    // replication when a treatment begins or finishes.
    [{
        private _keep = [];
        {
            _x params ["_medic", "_patient", "_epoch", "_trackedOwner", "_receivedAt"];
            if (isNull _patient) then {continue;};
            private _session = _patient getVariable [QGVAR(BVM_session), []];
            if !(_session isEqualTo [_medic, _epoch]) then {
                // The track event can arrive before BVM_session replication.
                if (CBA_missionTime - _receivedAt < 3) then {_keep pushBack _x;};
            } else {
                if (isNull _medic || {!alive _medic} || {owner _medic != _trackedOwner}) then {
                    [_medic, _patient, _epoch] call FUNC(bvmRelease);
                } else {
                    _keep pushBack _x;
                };
            };
        } forEach GVAR(BVM_Sessions);
        GVAR(BVM_Sessions) = _keep;
    }, 1, []] call CBA_fnc_addPerFrameHandler;

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
