#include "..\script_component.hpp"
/*
 * Authoritative clinical wake gate.
 * Stable vitals are necessary, but every real unconsciousness blocker must also be clear.
 *
 * CBA state-machine transition conditions execute as: _listItem call _condition.
 * That means _this is the casualty OBJECT there, while ordinary callers use
 * [_patient, _ignoreKnockOut] call ACM_core_fnc_canWake. Accept both forms.
 */
private _patient = objNull;
private _ignoreKnockOut = false;

if (_this isEqualType objNull) then {
    _patient = _this;
} else {
    _this params [
        ["_patientArg", objNull, [objNull]],
        ["_ignoreArg", false, [false]]
    ];
    _patient = _patientArg;
    _ignoreKnockOut = _ignoreArg;
};

if (isNull _patient || {!alive _patient}) exitWith {false};
if !([_patient] call ACEFUNC(medical_status,hasStableVitals)) exitWith {false};
if (!_ignoreKnockOut && {_patient getVariable [QGVAR(KnockOut_State), false]}) exitWith {false};

!([_patient] call FUNC(isForcedUnconscious))
