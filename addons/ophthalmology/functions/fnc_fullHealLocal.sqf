#include "..\script_component.hpp"
/*
 * Full definitive reset for ocular state.
 */
params ["_patient"];
TRACE_1("fullHealLocal",_patient);
if (isNull _patient || {!local _patient}) exitWith {};

private _shield = hmd _patient;
if (_shield in ["kat_eyecovers_left","kat_eyecovers_right","kat_eyecovers"]) then {
    _patient unlinkItem _shield;
    _patient addItem _shield;
};

_patient setVariable [QGVAR(dustInjuryLight),0,true];
_patient setVariable [QGVAR(dustInjuryHeavy),0,true];
_patient setVariable [QGVAR(eyeInjuries),[1,1],true];
_patient setVariable [QGVAR(eyeInjurySevere),false,true];
_patient setVariable [QGVAR(ocularPermanent),false,true];
_patient setVariable [QGVAR(eyeShieldItem),"",true];
_patient setVariable [QGVAR(eyeShieldIndex),-1,true];
_patient setVariable [QGVAR(eyeShieldAppliedAt),-1,true];
_patient setVariable [QGVAR(structuralLastTick),-1,false];

if (hasInterface && {_patient isEqualTo ACE_player}) then {
    [] call FUNC(hideEyeShieldOverlay);
    [false,0] call FUNC(effectEyeInjury);
    [false,[1,1]] call FUNC(effectHurtEye);
};
