/* Re-enroll durable disease through each native component owner. Local clocks
 * never cross an ownership/clinical period; durable progression clocks retain
 * their CBA mission-time meaning and are rebased by the snapshot codec.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

private _period = [clientOwner, _patient getVariable ["ACME_providerLocalityEpoch", 0],
    [_patient] call ACME_fnc_clinicalEpoch];
private _newPeriod = (_patient getVariable ["ACME_medmashLocalPeriod", []]) isNotEqualTo _period;
if (_newPeriod) then {_patient setVariable ["ACME_medmashLocalPeriod", _period, false];};

// Registry membership, native clocks and derived outputs belong to their
// component. The ACME coordinator never becomes a second native-state writer.
if (!isNil "ACM_burns_fnc_reconcile") then {[_patient, _newPeriod, false] call ACM_burns_fnc_reconcile;};
if (!isNil "ACM_infection_fnc_reconcile") then {[_patient, _newPeriod, false] call ACM_infection_fnc_reconcile;};
if (!isNil "ACM_ophthalmology_fnc_reconcile") then {[_patient, _newPeriod, false] call ACM_ophthalmology_fnc_reconcile;};
