params [["_unit",objNull,[objNull]]];
if !([_unit] call ACME_fnc_medicalLitterCanCollect) exitWith {false};
private _serial = (_unit getVariable ["ACME_litterSerial",0]) + 1;
_unit setVariable ["ACME_litterSerial",_serial];
private _request = format ["litter:%1:%2:%3",clientOwner,diag_tickTime,_serial];
_unit setVariable ["ACME_litterCollect",[_request,"","request",diag_tickTime + 15,_unit getVariable ["ACME_providerLocalityEpoch",0]]];
["ACME_medicalLitter",["request",_unit,clientOwner,_request,""]] call CBA_fnc_serverEvent;
// Bounded recovery if a grant/reply is delayed or the controlled unit/locality changes.
[{
    params ["_unit","_request"];
    private _state = _unit getVariable ["ACME_litterCollect",[]];
    if ((_state param [0,""]) == _request) then {[_unit,_request,_state param [1,""],false] call ACME_fnc_medicalLitterFinish;};
},[_unit,_request],15] call CBA_fnc_waitAndExecute;
true
