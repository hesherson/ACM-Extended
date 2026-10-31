/* Replies are accepted only by the pending local request; unsolicited/duplicate grants never animate. */
params [["_unit",objNull,[objNull]],["_request","",[""]],["_result","",[""]],["_token","",[""]],["_count",0,[0]]];
if (isNull _unit || {!local _unit} || {_unit isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
private _state = _unit getVariable ["ACME_litterCollect",[]];
if (count _state != 5 || {(_state select 0) != _request}
    || {diag_tickTime >= (_state select 3)}
    || {(_state select 4) != (_unit getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {};
if (_result == "grant") exitWith {
    if ((_state select 2) != "request" || {_token == ""}) exitWith {};
    _state set [1,_token];
    if !([_unit,true] call ACME_fnc_medicalLitterCanCollect) exitWith {[_unit,_request,_token,false] call ACME_fnc_medicalLitterFinish;};
    [_unit,_request,_token] call ACME_fnc_medicalLitterAnimate;
};
if (_result == "cancelled" && {(_state select 1) == _token}) exitWith {
    [_unit,_request,_token,false] call ACME_fnc_medicalLitterFinish;
};
if (_result == "done" && {(_state select 2) == "commit"} && {(_state select 1) == _token}) exitWith {
    _unit setVariable ["ACME_litterCollect",[]];
    [format ["Collected %1 medical litter object(s).",_count],2,_unit] call ace_common_fnc_displayTextStructured;
};
if (_result in ["none","busy"] && {(_state select 2) == "request"}) then {
    _unit setVariable ["ACME_litterCollect",[]];
    [["No registered medical litter within reach.","A collection request is already active."] select (_result == "busy"),2,_unit] call ace_common_fnc_displayTextStructured;
};
