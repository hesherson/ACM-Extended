/* Called by the native needle-withdrawal completion INSTEAD of registering a skin IV. */
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
if (isNull _d || {!(_d getVariable ["ACME_IV_FieldInserting",false])}) exitWith {};
private _m=uiNamespace getVariable ["ACME_IV_Medic",objNull];
private _p=_m getVariable ["ACME_IV_FinishPending",[]];
private _active=+(_d getVariable ["ACME_IV_FinishActive",[]]);
if (count _p<9 || {count _active<3} || {!((_p select 7) call ACME_fnc_ivMinigameViewValid)}) exitWith {[] call ACME_fnc_ivFinishAbort;};
_d setVariable ["ACME_IV_FieldFrame",13];_d setVariable ["ACME_IV_FieldProgressAt",-1];
uiNamespace setVariable ["ACME_IV_InsFrame",13];
[] call ACME_fnc_ivFieldProgress;
uiNamespace setVariable ["ACME_IV_InsStage",""];
uiNamespace setVariable ["ACME_IV_Dragging",false];uiNamespace setVariable ["ACME_IV_Held","none"];
private _c=uiNamespace getVariable ["ACME_IV_CathCtrl",controlNull];
if (!isNull _c) then {
    [_c,[uiNamespace getVariable ["ACME_IV_InsGauge",16],uiNamespace getVariable ["ACME_IV_InsSuffix",""],14] call ACME_fnc_ivCathTex] call ACME_fnc_ivCathSetFrame;
};
_active set [2,true];_d setVariable ["ACME_IV_FinishActive",_active];
[_p select 0,"ivFinish",[_m,"finish",_p select 2,_p select 3,_p select 1,_p select 4,_p select 5]] call ACME_fnc_ownerDispatch;
