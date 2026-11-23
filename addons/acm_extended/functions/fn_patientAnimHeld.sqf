/* B393: is a casualty's body held by a provider's animation lease right now (ACME_patientAnimLock, written by
 * fn_patientAnimRequest.sqf on the casualty's owner, public)? Code that keeps a pose by re-applying it (the litter
 * pose guard, the HPMK wrap pose, the pose another machine forces locally) asks this first and stands aside while
 * a lease runs, so that two systems never take turns overwriting the same casualty.
 * [_patient, _exceptSources] call ACME_fnc_patientAnimHeld: _exceptSources (lower case) are leases that do not count. */
params [["_patient", objNull, [objNull]], ["_exceptSources", [], [[]]]];
if (isNull _patient) exitWith {false};
private _lock = _patient getVariable ["ACME_patientAnimLock", []];
(count _lock) >= 5 && {(_lock param [4, -1]) > serverTime} && {!((toLowerANSI (_lock param [1, ""])) in _exceptSources)}
