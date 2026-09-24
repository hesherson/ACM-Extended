// Owner-side identified lease for temporary chest-access plate-carrier removal.
params [
    ["_patient", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_id", "", [""]],
    ["_start", true, [false]],
    ["_classname", "", [""]]
];
if (isNull _patient || {_id == ""}) exitWith {};
if (!local _patient) exitWith {[_patient, "chestAccessVestEvent", _this] call ACME_fnc_ownerDispatch;};

private _leases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
if (_start) then {
    _leases set [_id, [_medic, CBA_missionTime, toLowerANSI _classname]];
    _patient setVariable ["ACME_chestAccess_readyLease", _id, true];
    _patient setVariable ["ACME_chestAccess_readyServer", -1, true];
} else {
    _leases deleteAt _id;
};
_patient setVariable ["ACME_chestAccess_leases", _leases, true];
if (!_start && {(count _leases) == 0}) then {
    _patient setVariable ["ACME_chestAccess_readyLease", "", true];
};

// Thoracostomy is a long minigame rather than one treatment timer. Publish a procedure flag from the live lease
// set so a roll or another action cannot return the carrier before the thoracostomy screen actually closes.
private _thoraActive = false;
{
    private _entry = _leases get _x;
    if ((_entry param [2,"",[""]]) == "thoracostomy") exitWith {_thoraActive = true;};
} forEach keys _leases;
_patient setVariable ["ACME_Thora_ChestAccessActive", _thoraActive, true];

if (_start) then {
    private _busyBefore = _patient getVariable ["ACME_chestAccess_vestBusy", ""];
    [_patient, _medic, "access"] call ACME_fnc_chestAccessVestAcquire;

    // A new intervention outranks a carrier-return animation, but do not tear the patient's current RTM/physics
    // out from underneath it. Queue the same exact lease immediately behind the short restore. The lease-id check
    // makes the retry harmless if the provider cancels Preparing... before restoration finishes.
    if ((_busyBefore find "restore:access:") == 0) then {
        [{
            params ["_p","_id"];
            isNull _p
                || {!local _p}
                || {!(_id in keys (_p getVariable ["ACME_chestAccess_leases", createHashMap]))}
                || {(_p getVariable ["ACME_chestAccess_vestBusy", ""]) == ""}
        }, {
            params ["_p","_id","_m"];
            if (isNull _p || {!local _p}) exitWith {};
            if !(_id in keys (_p getVariable ["ACME_chestAccess_leases", createHashMap])) exitWith {};
            [_p, _m, "access"] call ACME_fnc_chestAccessVestAcquire;
        }, [_patient,_id,_medic], 2.5] call CBA_fnc_waitUntilAndExecute;
    };
} else {
    if ((count _leases) == 0) then {
        // Cancel only an unfinished ACCESS removal episode. Clearing its exact busy token makes every delayed
        // lift/remove/lower callback fail its generation check before it can touch gear or patient animation.
        private _busy = _patient getVariable ["ACME_chestAccess_vestBusy", ""];
        if ((_busy find "vest:access:") == 0) then {
            _patient setVariable ["ACME_chestAccess_vestBusy", "", false];
            _patient setVariable ["ACME_chestAccess_readyServer", serverTime, true];
        };

        [_patient, false, _medic, "access"] call ACME_fnc_chestAccessVestRestore;

        // A preparation canceled before ACE treatmentStarted has no head-elevation treatment lease to release.
        // If it temporarily flattened Semi-Fowler, explicitly arm the ordinary deferred resume instead of leaving
        // the patient flat or replaying elevation under another intervention.
        if ((_patient getVariable ["ACME_headElevated", false])
            && {_patient getVariable ["ACME_headElev_Suspended", false]}
            && {(count (_patient getVariable ["ACME_headElev_treatments", createHashMap])) == 0}) then {
            _patient setVariable ["ACME_headElev_ResumePending", true, true];
            private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
            [{_this call ACME_fnc_headElevTryResume;}, [_patient, _poseToken], 0.20] call CBA_fnc_waitAndExecute;
        };
    };
};
