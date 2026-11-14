/* The server reads the CBA Server source and publishes one authoritative, JIP-safe policy.
 * The client never evaluates Client or Mission addon-settings values for this policy. */
if (isRemoteExecuted) exitWith {
    if (remoteExecutedOwner == 2 && {!isServer}) then {
        if (count _this == 12) then {missionNamespace setVariable ["ACME_clinicalTiming",_this];};
        if (count _this == 4) then {missionNamespace setVariable ["ACME_clinicalClockAnchor",_this];};
    };
};
if (!isServer) exitWith {};
private _settings = [
    "ACME_medicationTimeScale","ACME_bloodRealTime","ACME_bloodSpoilEnabled","ACME_sys_bloodChain",
    "ACME_persistentCooler1Hours","ACME_persistentCooler2Hours","ACME_persistentCooler4Hours",
    "ACME_bloodStoredWarmHours","ACME_bloodFreshHours","ACME_bloodSpikedHours","ACME_bloodFridgeDays",
    "ACME_clinicalTimeBasis"
];
private _policy = _settings apply {[_x,"server"] call CBA_settings_fnc_get};
if (_policy isEqualTo (missionNamespace getVariable ["ACME_clinicalTiming",[]])) exitWith {};
missionNamespace setVariable ["ACME_clinicalTiming",_policy];
_policy remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalTiming"];
call ACME_fnc_clinicalClockTick;
if ((_policy param [11,0]) == 1) then {
    if (isNil "ACME_clinicalClockPFH") then {
        ACME_clinicalClockPFH = [{call ACME_fnc_clinicalClockTick;},0.25] call CBA_fnc_addPerFrameHandler;
    };
};
