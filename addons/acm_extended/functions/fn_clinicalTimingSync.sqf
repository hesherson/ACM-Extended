/* The server reads the CBA Server source and publishes one authoritative, JIP-safe policy.
 * The client never evaluates Client or Mission addon-settings values for this policy. */
if (isRemoteExecuted) exitWith {
    if (remoteExecutedOwner == 2 && {!isServer} && {count _this == 11}) then {
        missionNamespace setVariable ["ACME_clinicalTiming",_this];
    };
};
if (!isServer) exitWith {};
private _settings = [
    "ACME_medicationTimeScale","ACME_bloodRealTime","ACME_bloodSpoilEnabled","ACME_sys_bloodChain",
    "ACME_persistentCooler1Hours","ACME_persistentCooler2Hours","ACME_persistentCooler4Hours",
    "ACME_bloodStoredWarmHours","ACME_bloodFreshHours","ACME_bloodSpikedHours","ACME_bloodFridgeDays"
];
private _policy = _settings apply {[_x,"server"] call CBA_settings_fnc_get};
if (_policy isEqualTo (missionNamespace getVariable ["ACME_clinicalTiming",[]])) exitWith {};
missionNamespace setVariable ["ACME_clinicalTiming",_policy];
_policy remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalTiming"];
