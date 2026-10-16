/* Select a real seated hub, never a global 'last puncture' outcome. */
params ["_fx","_fy",["_override",""],["_exactUID",""]];
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
private _medic=uiNamespace getVariable ["ACME_IV_Medic",objNull];
private _patient=uiNamespace getVariable ["ACME_IV_Patient",objNull];
if (isNull _d || {isNull _medic} || {!local _medic} || {!([] call ACME_fnc_ivUiValid)}) exitWith {false};
if ((_medic getVariable ["ACME_IV_FinishPending",[]]) isNotEqualTo []) exitWith {true};
private _action=if (_override!="") then {_override} else {uiNamespace getVariable ["ACME_IV_Held","none"]};
if !(_action in ["extension","flush","dressing","line","lock","field14","field16","removeLock","removeSecondary","removeExtension","removeDressing","removeLine"]) exitWith {false};
private _bp=uiNamespace getVariable ["ACME_IV_BodyPart",""];
private _view=uiNamespace getVariable ["ACME_IV_View",""];
private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
if (count _r!=4) exitWith {false};
private _target=[(_r select 0)+(_r select 2)*_fx,(_r select 1)+(_r select 3)*_fy,_action,false,true] call ACME_fnc_ivFinishTarget;
private _best=if (_target isEqualTo []) then {[]} else {_target select 0};
if (_exactUID!="" && {_action in ["removeLock","removeSecondary","field14","field16","removeExtension","removeDressing","removeLine"]}) then {
    private _marks=_patient getVariable ["ACME_IV_Marks",[]];
    private _i=_marks findIf {(_x param [14,""])==_exactUID && {(_x param [4,""])=="hub"} && {(_x select 0)==_bp} && {(_x select 1)==_view}};
    _best=if (_i<0) then {[]} else {+(_marks select _i)};
};
if (_best isEqualTo []) exitWith {false};
private _uid=_best param [14,""];
if (_uid=="") exitWith {["Reopen the IV view to load this catheter.",2,_medic] call ace_common_fnc_displayTextStructured;true};
private _plan=[_best param [15,[false,false,false,false]],_action,true,_best param [7,0]] call ACME_fnc_ivFinishPlan;
if !(_plan select 0) exitWith {[_plan select 1,2,_medic] call ace_common_fnc_displayTextStructured;true};
private _receipt=[];
private _item=switch (_action) do {case "flush":{"ACM_SalineFlush_10"};case "field14":{"ACM_IV_14g"};case "field16":{"ACM_IV_16g"};default{""};};
if (_item!="") then {_receipt=[_medic,_patient,[_item]] call ACME_fnc_treatmentSupplyTake;};
if (_item!="" && {_receipt isEqualTo []}) exitWith {["The selected IV tool is not available.",2,_medic] call ace_common_fnc_displayTextStructured;true};
private _serial=(_medic getVariable ["ACME_IV_FinishSerial",0])+1;
_medic setVariable ["ACME_IV_FinishSerial",_serial];
private _token=format ["ivfinish:%1:%2:%3",clientOwner,netId _medic,_serial];
private _epoch=[_patient] call ACME_fnc_clinicalEpoch;
private _deadline=serverTime+(if (_action in ["field14","field16"]) then {90} else {30});
// Publish the exact reservation before sending BEGIN. The owner waits for
// replication rather than rejecting an otherwise valid first packet.
if (_receipt isNotEqualTo [] && {!([_medic,_patient,_uid,_action,_token,_epoch,_deadline,_receipt] call ACME_fnc_ivSupplyBind)}) exitWith {
    [_receipt] call ACME_fnc_treatmentSupplyRefund;
    ["The IV supply reservation is no longer available.",2,_medic] call ace_common_fnc_displayTextStructured;
    true
};
private _context=[_d,+(uiNamespace getVariable ["ACME_IV_Session",[]]),_d getVariable ["ACME_IV_ViewGeneration",0],_bp,_view];
private _pending=[_patient,_token,_uid,_action,_epoch,_deadline,_receipt,_context,false];
_medic setVariable ["ACME_IV_FinishPending",_pending];
_d setVariable ["ACME_IV_FinishBusy",true];
uiNamespace setVariable ["ACME_IV_Held","none"];
if !(_action in ["field14","field16"]) then {uiNamespace setVariable ["ACME_IV_Dragging",false];};
(uiNamespace getVariable ["ACME_IV_HeldCursorCtrl",controlNull]) ctrlShow false;
[_patient,"ivFinish",[_medic,"begin",_uid,_action,_token,_epoch,_deadline,_receipt]] call ACME_fnc_ownerDispatch;
[{_this call ACME_fnc_ivFinishRetry;},[_medic,_token],1] call CBA_fnc_waitAndExecute;
playSound "ACE_Sound_Click";
true
