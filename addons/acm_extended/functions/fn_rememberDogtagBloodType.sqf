/* Called after successful local dogtag display. Object identity isolates medics
   and replacement/respawn patient units. Nothing is broadcast. */
params [["_observer", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_data", [], [[]]]];
if (!hasInterface || {isNull _observer} || {isNull _patient} || {_observer != ACE_player}) exitWith {false};
if (count _data < 3) exitWith {false};
private _blood = _data param [2, "", [""]];
if !(_blood in ["A+","A-","B+","B-","AB+","AB-","O+","O-"]) exitWith {false};
private _entries = (uiNamespace getVariable ["ACME_dogtagBloodKnowledge", []]) select {
    !isNull (_x param [0, objNull]) && {!isNull (_x param [1, objNull])}
};
private _index = _entries findIf {(_x param [0, objNull]) isEqualTo _observer && {(_x param [1, objNull]) isEqualTo _patient}};
if (_index >= 0) then {_entries set [_index, [_observer, _patient, _blood]];} else {_entries pushBack [_observer, _patient, _blood];};
uiNamespace setVariable ["ACME_dogtagBloodKnowledge", _entries];
true
