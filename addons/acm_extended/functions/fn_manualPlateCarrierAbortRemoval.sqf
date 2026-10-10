/* B264: abort only the still-"removing" patient-owned lease. The old
 * machine is allowed to forward the request after a locality transfer. */
params [
    ["_p", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_lease", "", [""]],
    ["_reason", "remove-timeout", [""]]
];
if (isNull _p || {_lease == ""}) exitWith {false};
if (!local _p) exitWith {
    [_p, "manualPlateCarrierAbortRemoval", [_p, _medic, _lease, _reason]] call ACME_fnc_ownerDispatch;
    true
};
if ((_p getVariable ["ACME_manualPlateCarrierLease", ""]) != _lease
    || {(_p getVariable ["ACME_manualPlateCarrierState", ""]) != "removing"}) exitWith {false};
diag_log format ["[ACME MANUAL PC B264] removal aborted patient=%1 owner=%2 lease=%3 reason=%4 vest=%5 saved=%6",
    netId _p, owner _p, _lease, _reason, vest _p,
    count (_p getVariable ["ACME_chestAccess_vestLoadout", []])];
[_p, _reason] call ACME_fnc_manualPlateCarrierAutoReturn;
if (!isNull _medic) then {
    ["ACME_manualPlateCarrierAck", [_p, false, false], _medic] call CBA_fnc_targetEvent;
};
true
