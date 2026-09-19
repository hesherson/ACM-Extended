// Experimental drag handles are available only in HEMTT dev/launch builds.
if (getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acme_developmentBuild") != 1) exitWith {};
// ACME hands-free ragdoll drag handle.
// Physics stays patient-owner authoritative; provider locomotion is local.
if (missionNamespace getVariable ["ACME_dragHandle_runtimeInstalled",false]) exitWith {};
missionNamespace setVariable ["ACME_dragHandle_runtimeInstalled",true];

// First-pass tuning. All are missionNamespace values on purpose so they can be dialed in live without changing
// transaction structure.
if (isNil "ACME_dragHandle_enabled") then {ACME_dragHandle_enabled = true;};
if (isNil "ACME_dragHandle_attachDistance") then {ACME_dragHandle_attachDistance = 2.3;};
if (isNil "ACME_dragHandle_slackLength") then {ACME_dragHandle_slackLength = 1.0;};
if (isNil "ACME_dragHandle_releaseDistance") then {ACME_dragHandle_releaseDistance = 2.65;};
if (isNil "ACME_dragHandle_springAccelPerM") then {ACME_dragHandle_springAccelPerM = 8.0;};
if (isNil "ACME_dragHandle_damping") then {ACME_dragHandle_damping = 2.1;};
if (isNil "ACME_dragHandle_maxAccel") then {ACME_dragHandle_maxAccel = 5.2;};
if (isNil "ACME_dragHandle_lightAnimCoef") then {ACME_dragHandle_lightAnimCoef = 0.62;};
if (isNil "ACME_dragHandle_heavyAnimCoef") then {ACME_dragHandle_heavyAnimCoef = 0.48;};

["ACME_dragHandle_startAck",{
    params ["_medic","_patient","_ok","_weight",["_reason",""],["_session",""]];
    if (isNull _medic || {!local _medic}) exitWith {};
    _medic setVariable ["ACME_dragHandle_pending",false];
    if (_ok) then {
        // Seed the authoritative values locally before applying provider restrictions. Public-variable replication
        // and the targeted acknowledgement use different network paths and are not required to arrive in lockstep.
        if (_session != "" && {(_medic getVariable ["ACME_dragHandle_lastStoppedSession",""]) == _session}) exitWith {};
        _patient setVariable ["ACME_dragHandle_active",true];
        _patient setVariable ["ACME_dragHandle_dragger",_medic];
        _patient setVariable ["ACME_dragHandle_weight",_weight];
        _patient setVariable ["ACME_dragHandle_session",_session];
        [_medic,_patient,_weight,_session] call ACME_fnc_dragHandleStartMedic;
    } else {
        if (_reason != "") then {[_reason,1.8,_medic,12] call ace_common_fnc_displayTextStructured;};
    };
}] call CBA_fnc_addEventHandler;

["ACME_dragHandle_stopped",{
    params ["_medic","_patient",["_reason","manual"],["_session",""]];
    if (!isNull _medic && {local _medic}) then {
        if (_session != "") then {_medic setVariable ["ACME_dragHandle_lastStoppedSession",_session];};
        [_medic,_patient,_reason,_session] call ACME_fnc_dragHandleStopMedic;
    };
}] call CBA_fnc_addEventHandler;

// Advanced Fatigue gets a multiplicative workload rather than direct stamina edits. Casualty load and a tight
// tether both raise duty, so a heavy snag costs more than a smooth light-casualty drag.
if (!isNil "ace_advanced_fatigue_fnc_addDutyFactor"
    && {!(missionNamespace getVariable ["ACME_dragHandle_dutyRegistered",false])}) then {
    missionNamespace setVariable ["ACME_dragHandle_dutyRegistered",true];
    ["ACME_dragHandle",{
        private _p = ACE_player getVariable ["ACME_dragHandle_patient",objNull];
        if (isNull _p) exitWith {1};
        private _w = ACE_player getVariable ["ACME_dragHandle_weight",350];
        private _t = ACE_player getVariable ["ACME_dragHandle_tension",0];
        (linearConversion [350,950,_w,1.15,1.70,true])
        * (linearConversion [0,1,_t,1,1.35,true])
    }] call ace_advanced_fatigue_fnc_addDutyFactor;
};

// Patient and self ACE interactions are config-native in CfgVehicles.
// The patient owner creates one networked ACE fast-roping helper/rope pair per session.
// Engine replication supplies JIP visuals; clients must not draw or create duplicate tethers.
