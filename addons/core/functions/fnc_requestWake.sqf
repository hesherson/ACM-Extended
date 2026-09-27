#include "..\script_component.hpp"
/* One clinical wake request. The normal ACE event runs first. A refused or
 * desynchronized transition is reconciled against its actual CBA state, never
 * against an arbitrary elapsed-time threshold. No delayed worker is created here.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_ignoreKnockOut", false, [false]],
    ["_reason", "clinical", [""]]
];
if (isNull _patient || {!alive _patient} || {!local _patient}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {false};
if !([_patient, _ignoreKnockOut] call FUNC(canWake)) exitWith {false};
if (_ignoreKnockOut && {_patient getVariable [QGVAR(KnockOut_State), false]}) then {
    _patient setVariable [QGVAR(KnockOut_State), false, true];
};
if !([_patient] call FUNC(canWake)) exitWith {false};

// ACM wake posture contract: an on-foot casualty who regains consciousness wakes INTO ACM_LyingState and must
// use the normal Get Up action afterward. ACE calls setUnconsciousAnim(false) before publishing ace_unconscious,
// so this state must be armed before the WakeUp event. WasTreated is the legacy ACM handoff flag consumed by
// fnc_onUnconscious(false); Lying_State is also set now so even a repaired/desynchronized wake cannot fall through
// to ACE's ordinary prone/get-out animation branch.
if ((_patient getVariable ["ACE_isUnconscious", false]) && {isNull objectParent _patient}) then {
    [_patient, true, true] call FUNC(setWasTreated);
    [_patient, true, true] call FUNC(setLyingState);
};

[QACEGVAR(medical,WakeUp), _patient] call CBA_fnc_localEvent;
[_patient, _reason] call FUNC(reconcileWake)
