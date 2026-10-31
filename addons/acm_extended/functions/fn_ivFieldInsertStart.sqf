/* After owner reservation, drive the SAME manual catheter sequence used on skin. */
params ["_row"];
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
private _job=_row param [16,[]];
if (isNull _d || {count _job<7} || {!((_job select 2) in ["field14","field16"])}) exitWith {};
private _gauge=if ((_job select 2)=="field14") then {14} else {16};
private _child=[_row,_gauge] call ACME_fnc_ivFieldSecondaryRow;
if (_child isEqualTo []) exitWith {[] call ACME_fnc_ivFinishAbort;};
_d setVariable ["ACME_IV_FieldInserting",true];
_d setVariable ["ACME_IV_FieldJobSeen",false];
_d setVariable ["ACME_IV_FieldRow",_row];
_d setVariable ["ACME_IV_FieldFrame",1];
_d setVariable ["ACME_IV_FieldProgressAt",-1];
uiNamespace setVariable ["ACME_IV_Gauge",_gauge];
uiNamespace setVariable ["ACME_IV_NeedleFrame",_row param [6,""]];
uiNamespace setVariable ["ACME_IV_NeedleAngle",_row param [13,0]];
uiNamespace setVariable ["ACME_IV_StickAcc",0];
// Recreate the inactive native catheter control once so the held introducer is above the base film.
// The existing mark renderer owns the lock; never duplicate it above the primary hub.
private _old=uiNamespace getVariable ["ACME_IV_CathCtrl",controlNull];
if (!isNull _old) then {ctrlDelete _old;};
uiNamespace setVariable ["ACME_IV_CathCtrl",controlNull];
[_child select 2,_child select 3,false,_row param [10,""]] call ACME_fnc_ivMinigameInsertStart;
_d setVariable ["ACME_IV_FieldShell",controlNull];
(_d displayCtrl 86503) ctrlSetText "Push into the saline-lock port, then scroll to thread the catheter.";
