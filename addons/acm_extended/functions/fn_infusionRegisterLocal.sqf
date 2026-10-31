params ["_context", "_med", "_dose", "_duration", "_dropSet", "_drops", "_clamp", "_uid", "_bagUid", "_epoch", ["_receipt", []], ["_solutionMl", 0], ["_deferPublish", false]];
private _patient = _context select 0;
// Deferred publication is only an internal, receipt-free prepared-attach step.
if !(_receipt isEqualTo []) then {_deferPublish = false;};
if (!local _patient) exitWith {[_patient, "infusionRegister", _this] call ACME_fnc_ownerDispatch; ""};
if (_receipt isEqualTo []) exitWith {((_this select [0,10]) + [_solutionMl, _deferPublish]) call ACME_fnc_infusionRegisterCore;};
private _results = _patient getVariable ["ACME_infusionResults", createHashMap];
private _result = _results getOrDefault [_uid, []];
if (_result isEqualTo []) then {
    private _medic = _receipt param [0, objNull, [objNull]];
    private _near = !isNull _medic && {alive _medic} && {_medic distance _patient <= 5 || {!isNull objectParent _medic && {objectParent _medic == objectParent _patient}}};
    private _returned = if (_near) then {((_this select [0,10]) + [_solutionMl, _deferPublish]) call ACME_fnc_infusionRegisterCore} else {""};
    _result = [_returned != "", _returned];
    _results set [_uid, _result];
    if (count _results > 256) then {_results deleteAt ((keys _results) select 0);};
    _patient setVariable ["ACME_infusionResults", _results, true];
};
["ACME_infusionAck", [_uid, _result select 0], _receipt select 0] call CBA_fnc_targetEvent;
_result select 1
