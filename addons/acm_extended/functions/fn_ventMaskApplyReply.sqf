/* Provider-local ACK. Duplicates, late ACKs and successor actions cannot reanimate the medic. */
params [["_medic", objNull, [objNull]], ["_request", [], [[]]], ["_accepted", false, [false]]];
if (count _request != 6) exitWith {};
if (isNull _medic || {!local _medic}) exitWith {};
if !((_medic getVariable ["ACME_ventMaskPending", []]) isEqualTo _request) exitWith {};
_medic setVariable ["ACME_ventMaskPending", [], false];
if (serverTime > (_request param [4, -1]) || {!alive _medic}) exitWith {};
if (!_accepted) exitWith {
    ["NIV / CPAP mask could not be applied. Check the connected ventilator and your access.", 3, _medic] call ace_common_fnc_displayTextStructured;
};
[_medic, "mask", "", _request select 5] call ACME_fnc_headElevMedicSeq;
