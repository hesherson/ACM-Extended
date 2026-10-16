/* Owner-side arrest edge, independent of the seizure diagnosis. Server clock survives owner changes.
   Repeated arrest notifications cannot restart the motor window. This never treats a seizure. */
params ["_patient", "_active"];
if (isNull _patient || {!local _patient}) exitWith {};
if (!_active) exitWith {_patient setVariable ["ACME_seizure_arrestStartedAt", -1, true];};
if ((_patient getVariable ["ACME_seizure_arrestStartedAt", -1]) >= 0) exitWith {};
private _onset = serverTime;
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
_patient setVariable ["ACME_seizure_arrestStartedAt", _onset, true];
[{
    params ["_patient", "_onset", "_epoch"];
    if (isNull _patient || {!local _patient} || {!alive _patient}
        || {([_patient] call ACME_fnc_clinicalEpoch) != _epoch}
        || {(_patient getVariable ["ACME_seizure_arrestStartedAt", -1]) != _onset}
        || {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
        || {(_patient getVariable ["ACME_lido_seizureState", ""]) != "active"}) exitWith {};
    [_patient, true] call ACME_fnc_seizureMotion;
}, [_patient, _onset, _epoch], 20] call CBA_fnc_waitAndExecute;
