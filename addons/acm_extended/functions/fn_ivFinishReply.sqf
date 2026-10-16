/* Provider-side ACK: settle only its exact pending supply reservation. A stale
   display may retire the request but can never restart its animation. */
params ["_medic","_patient","_token","_status","_accepted",["_message",""],["_row",[]]];
if (isNull _medic || {!local _medic}) exitWith {};
private _pending=+(_medic getVariable ["ACME_IV_FinishPending",[]]);
if (count _pending<9 || {!((_pending select 0) isEqualTo _patient)} || {(_pending select 1)!=_token}) exitWith {};
private _receipt=_pending select 6;
if (_receipt isNotEqualTo []) then {
    [_medic,_token,_receipt] call ACME_fnc_ivSupplyRelease;
    [_receipt,!_accepted] call ACME_fnc_treatmentSupplyRefund;
    _pending set [6,[]];_medic setVariable ["ACME_IV_FinishPending",_pending];
};
private _context=_pending select 7;
private _valid=!(_pending select 8) && {_context call ACME_fnc_ivMinigameViewValid};
private _d=_context select 0;
if (_status=="begin" && {_accepted} && {_valid}) exitWith {
    if ((_d getVariable ["ACME_IV_FinishActive",[]]) isEqualTo []) then {
        _d setVariable ["ACME_IV_FinishActive",[_row,diag_tickTime,false]];
        [] call ACME_fnc_ivMinigameRenderMarks;
        [] call ACME_fnc_ivMinigameRefreshBandSlot;
        if ((_pending select 3) in ["field14","field16"]) then {[_row] call ACME_fnc_ivFieldInsertStart;};
    };
};
if (_status=="begin" && {_accepted}) exitWith {
    [_patient,"ivFinish",[_medic,"cancel",_pending select 2,_pending select 3,_token,_pending select 4,_pending select 5]] call ACME_fnc_ownerDispatch;
};
if (_valid && {(_pending select 3) in ["field14","field16"]}) then {[] call ACME_fnc_ivFieldClear;};
_medic setVariable ["ACME_IV_FinishPending",[]];
if (!isNull _d) then {_d setVariable ["ACME_IV_FinishActive",[]];_d setVariable ["ACME_IV_FinishBusy",false];};
if (_valid) then {
    if (_message!="") then {[_message,3,_medic] call ace_common_fnc_displayTextStructured;};
    [] call ACME_fnc_ivMinigameRenderMarks;
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
