// server-side: the megacode manikin has met fatal criteria. it must not die.
// instead it announces the death on the panel of the operator, flatlines the monitor and drops the manikin
// unconscious to mimic death, then after a short beat fully resets to baseline so the tool is immediately
// reusable.
// _this is [_d].
params ["_d"];
if (isNull _d || {!local _d}) exitWith {};
if (_d getVariable ["ACME_MC_dying", false]) exitWith {};
_d setVariable ["ACME_MC_dying", true, true];

private _op = _d getVariable ["ACME_MC_operatorClient", objNull];

// flatline the monitor for the death beat: asystole and no pulse.
[_d, 1] call ACME_fnc_rhythmSet;
[_d, 1, true, false] call ACME_fnc_rhythmActiveCommit;
_d setVariable ["ACME_MC_rhythm", "asystole", true];
_d setVariable ["ACME_MC_pulseless", true, true];
_d setVariable ["ACME_MC_HR", 0, true];

// drop them unconscious to mimic death, where local, meaning the server. it is only meaningful while still alive,
// and on an actual corpse, which is the true-death backstop, this is a no-op and the delayed reset below will
// respawn instead.
if (alive _d && {!(_d getVariable ["ACE_isUnconscious", false])}) then {
    [_d, true] call ace_medical_status_fnc_setUnconsciousState;
};

// announce it on the panel of the operator, as a toast and a red log line, if they have or had it open.
if (!isNull _op) then {
    ["MEGACODE KELLY DIED. Resetting.", 4] remoteExec ["ace_common_fnc_displayTextStructured", _op];
    [["PATIENT DIED. Resetting...", "#ff5555"]] remoteExec ["ACME_fnc_megacodeLog", _op];
};

// after the death beat: a full reset and a refresh of the panel of the operator.
[{
    params ["_d", "_op"];
    if (isNull _d) exitWith {};
    [_d] call ACME_fnc_megacodeResetUnit;  // clears the dying latch + restores baseline (or respawns a true corpse)
    // refresh the operator's open panel on their own page (the server's uiNamespace knows nothing of it). a corpse
    // that was respawned instead is re-pointed by ACME_fnc_megacodeRespawn itself.
    if (!isNull _op && {!isNull _d} && {alive _d}) then {
        [_d] remoteExec ["ACME_fnc_megacodePanelRetarget", _op];
    };
}, [_d, _op], missionNamespace getVariable ["ACME_megacode_deathBeat", 3.0]] call CBA_fnc_waitAndExecute;
