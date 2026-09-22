#include "..\script_component.hpp"
/*
 * Authoritative clinical wake gate.
 * Stable vitals are necessary, but every real unconsciousness blocker must also be clear.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_ignoreKnockOut", false, [false]]
];

if (isNull _patient || {!alive _patient}) exitWith {false};
if !([_patient] call ACEFUNC(medical_status,hasStableVitals)) exitWith {false};
if (!_ignoreKnockOut && {_patient getVariable [QGVAR(KnockOut_State), false]}) exitWith {false};

!([_patient] call FUNC(isForcedUnconscious))
