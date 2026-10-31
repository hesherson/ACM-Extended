/* B275: knowledge for the local observer and this exact patient instance.
   The public patient dogtag/blood-type cache never implies it was inspected. */
params [["_observer", objNull, [objNull]], ["_patient", objNull, [objNull]]];
if (!hasInterface || {isNull _observer} || {isNull _patient} || {_observer != ACE_player}) exitWith {"???"};
private _entries = uiNamespace getVariable ["ACME_dogtagBloodKnowledge", []];
private _index = _entries findIf {(_x param [0, objNull]) isEqualTo _observer && {(_x param [1, objNull]) isEqualTo _patient}};
if (_index < 0) exitWith {"???"};
(_entries select _index) param [2, "???"]
