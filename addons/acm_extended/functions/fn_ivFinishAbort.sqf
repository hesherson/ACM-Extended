/* Cancel only the outgoing IV view's job. No patient or provider animation reset. */
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
private _medic=uiNamespace getVariable ["ACME_IV_Medic",objNull];
[] call ACME_fnc_ivFieldClear;
if (!isNull _d) then {_d setVariable ["ACME_IV_FlushPullPin",[]];};
if (isNull _medic) exitWith {};
private _p=+(_medic getVariable ["ACME_IV_FinishPending",[]]);
if (count _p>=9 && {((_p select 7) select 0) isEqualTo _d}) then {
    _p set [8,true];_medic setVariable ["ACME_IV_FinishPending",_p];
    [_p select 0,"ivFinish",[_medic,"cancel",_p select 2,_p select 3,_p select 1,_p select 4,_p select 5]] call ACME_fnc_ownerDispatch;
};
if (!isNull _d) then {_d setVariable ["ACME_IV_FinishActive",[]];_d setVariable ["ACME_IV_FinishBusy",false];};
