#include "..\script_component.hpp"
/* B258: circulation-owned cleanup of machine-local CPR AnimDone ownership.
   Called by ACME's general locality handler on both edges. This does not
   change a patient reservation, clinical epoch or another provider's input. */
params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith {false};
// B373: a provider that changes owner must not stay attached to the casualty by an episode that ended here.
private _held = _unit getVariable [QGVAR(CPR_Attached), objNull];
if (!isNull _held) then {
    if (local _unit && {(attachedTo _unit) in [_held, _unit getVariable [QGVAR(CPR_Anchor), _held]]}) then {detach _unit;};
    _unit setVariable [QGVAR(CPR_Attached), objNull, false];
    _unit setVariable [QGVAR(CPR_Anchor), objNull, false];
    _unit setVariable [QGVAR(CPR_Align), [], false];
};
private _handler = _unit getVariable [QGVAR(CPR_AnimEH), -1];
if (_handler < 0) exitWith {false};
_unit removeEventHandler ["AnimDone", _handler];
_unit setVariable [QGVAR(CPR_AnimEH), -1, false];
_unit setVariable [QGVAR(CPR_AnimLocalityEpoch), -1, false];
_unit setVariable [QGVAR(CPR_Loop), false, false];
true
