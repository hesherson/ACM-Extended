/* Retransmit ordered milestones using the existing bounded owner job; no new PFH.
   Delayed/out-of-order stage packets cannot skip a previous milestone. */
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
if (isNull _d || {!(_d getVariable ["ACME_IV_FieldInserting",false])}) exitWith {};
private _m=uiNamespace getVariable ["ACME_IV_Medic",objNull];
private _p=_m getVariable ["ACME_IV_FinishPending",[]];
if (count _p<9 || {_p select 8}) exitWith {};
private _frame=(uiNamespace getVariable ["ACME_IV_InsFrame",1]) max (_d getVariable ["ACME_IV_FieldFrame",1]);
if (diag_tickTime<(_d getVariable ["ACME_IV_FieldProgressAt",-1])+0.4) exitWith {};
_d setVariable ["ACME_IV_FieldProgressAt",diag_tickTime];
{
    _x params ["_minimum","_phase"];
    if (_frame>=_minimum) then {
        [_p select 0,"ivFinish",[_m,_phase,_p select 2,_p select 3,_p select 1,_p select 4,_p select 5]] call ACME_fnc_ownerDispatch;
    };
} forEach [[6,"advance"],[11,"thread"],[13,"retract"]];
