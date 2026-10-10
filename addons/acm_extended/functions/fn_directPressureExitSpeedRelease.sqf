/* Local effect on each receiver. Never restore a captured (possibly already accelerated)
   locomotion coefficient. Clear this exact DP speed lease and restore 1 only if still ours. */
params ["_medic", "_serial"];
if (isNull _medic) exitWith {};
if ((_medic getVariable ["ACME_DP_ExitSpeedOwner", -1]) != _serial) exitWith {};
_medic setVariable ["ACME_DP_ExitSpeedOwner", -1, false];
if (abs ((getAnimSpeedCoef _medic) - 1.5) < 0.01
    && {!([_medic] call ACME_fnc_providerAnimSpeedOwned)}) then {
    _medic setAnimSpeedCoef 1;
};
