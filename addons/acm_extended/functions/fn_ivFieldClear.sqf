/* Only local field-insertion presentation. Never retire an ordinary skin insertion. */
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
if (isNull _d || {!(_d getVariable ["ACME_IV_FieldInserting",false])}) exitWith {};
_d setVariable ["ACME_IV_FieldInserting",false];_d setVariable ["ACME_IV_FieldRow",[]];
_d setVariable ["ACME_IV_FieldFrame",0];
_d setVariable ["ACME_IV_FieldJobSeen",false];
private _shell=_d getVariable ["ACME_IV_FieldShell",controlNull];
if (!isNull _shell) then {ctrlDelete _shell;};_d setVariable ["ACME_IV_FieldShell",controlNull];
private _h=_d getVariable ["ACME_IV_RetractPFH",-1];
if (_h>=0) then {[_h] call CBA_fnc_removePerFrameHandler;};
_d setVariable ["ACME_IV_RetractPFH",-1];
{uiNamespace setVariable [_x select 0,_x select 1];} forEach [
    ["ACME_IV_InsStage",""],["ACME_IV_InsFrame",0],["ACME_IV_InsProg",0],
    ["ACME_IV_Held","none"],["ACME_IV_Dragging",false],["ACME_IV_Stage","ready"],
    ["ACME_IV_InsSite",""],["ACME_IV_InsPin",[]],["ACME_IV_LastNeedleState",[]]
];
{private _c=uiNamespace getVariable [_x,controlNull];if (!isNull _c) then {_c ctrlShow false;};}
    forEach ["ACME_IV_CathCtrl","ACME_IV_CathGhost","ACME_IV_HeldCursorCtrl"];
