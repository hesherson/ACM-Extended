/* B264: patient-owner idempotent completion for persistent manual carrier
 * removal. Both the original wait callback and a migrated new owner can call
 * this; only the matching "removing" lease can emit an activity entry. */
params [
    ["_p", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_lease", "", [""]]
];
if (isNull _p || {!local _p} || {_lease == ""}) exitWith {false};
if ((_p getVariable ["ACME_manualPlateCarrierLease", ""]) != _lease
    || {(_p getVariable ["ACME_manualPlateCarrierState", ""]) != "removing"}) exitWith {false};
private _saved = _p getVariable ["ACME_chestAccess_vestLoadout", []];
private _ready = _p getVariable ["ACME_chestAccess_readyServer", -1];
if ((count _saved) != 2 || {vest _p != ""} || {_ready < 0}
    || {serverTime < _ready} || {(_p getVariable ["ACME_chestAccess_vestBusy", ""]) != ""}) exitWith {false};

_p setVariable ["ACME_manualPlateCarrierState", "off", true];
["ACME_manualPlateCarrierTrack", [_p]] call CBA_fnc_localEvent;
_p setVariable ["ACME_manualPlateCarrierRemoved", true, true];
_p setVariable ["ACME_manualPlateCarrierStartedAt", -1, true];
if (!isNull _medic) then {
    [_medic, "chestAccessVestProvider", [_medic, _p, "manualstop", false, "", _lease]]
        call ACME_fnc_ownerDispatch;
};
if ((_p getVariable ["ACME_headElevated", false])
    && {_p getVariable ["ACME_headElev_Suspended", false]}) then {
    if ((backpack _p) == "") then {
        [_p, "borrow"] call ACME_fnc_manualPlateCarrierHeadElevSupport;
    };
    _p setVariable ["ACME_headElev_ResumePending", true, true];
    private _poseToken = _p getVariable ["ACME_headElev_poseToken", ""];
    [{_this call ACME_fnc_headElevTryResume;}, [_p, _poseToken], 0.05] call CBA_fnc_waitAndExecute;
};
[_p, "activity", "Plate carrier manually removed", []] call ace_medical_treatment_fnc_addToLog;
if (!isNull _medic) then {
    ["ACME_manualPlateCarrierAck", [_p, false, true], _medic] call CBA_fnc_targetEvent;
};
true
