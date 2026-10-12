/* Only already-debited cylinder gas can enrich a breath. Settings remain untouched. */
params [["_patient",objNull,[objNull]],["_requested",-1,[0]]];
if (_requested<0) then {_requested=_patient getVariable ["ACME_vent_effectiveFiO2",21];};
if (!(_requested isEqualType 0) || {!finite _requested}) exitWith {21};
if (!(([_patient] call ACME_fnc_ventOxygenState) select 1)
) exitWith {21};
_requested max 21 min 95
