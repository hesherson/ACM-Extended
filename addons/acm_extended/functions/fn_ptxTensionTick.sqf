/* One patient-owner controller within the existing clinical scheduler. */
params [["_patient",objNull,[objNull]]];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if ((_patient getVariable ["ACM_breathing_Pneumothorax_State",0])<=0
    && {!(_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false])}
    && {count (_patient getVariable ["ACME_ptx_state",[]])==0}) exitWith {};
private _s=[_patient] call ACME_fnc_ptxEnsure;
// Eligible surface wounds/hemothorax alone must not create a PTX episode.
if ((_s select 6)==0 && {(_s select 1)<=0} && {(_s select 2)<=0}
    && {!(_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false])}) exitWith {};
private _dt=[_patient,"ptx",0.25,5] call ACME_fnc_clinicalTickDelta;
private _context=[_patient] call ACME_fnc_ptxContext;
private _result=[_s,_context,_dt,_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false],
    missionNamespace getVariable ["ACME_ptx_tensionBaseSec",600],
    missionNamespace getVariable ["ACME_ptx_leakSettleSec",600],
    missionNamespace getVariable ["ACME_ptx_stableSec",60],
    missionNamespace getVariable ["ACME_ptx_resolveSec",600]] call ACME_fnc_ptxStep;
_result params ["_next","_tension"];
[_patient,_next,_tension] call ACME_fnc_ptxPublish;
if (_tension) then {
    private _at=_patient getVariable ["ACM_breathing_TensionPneumothorax_Time",CBA_missionTime];
    private _ramp=missionNamespace getVariable ["ACME_ptx_tensionRampSec",90];
    private _sev=if (_ramp<=0) then {1} else {((CBA_missionTime-_at)/_ramp) max 0 min 1};
    [_patient,"ACME_ptx_tensionSeverity",_sev,0.02,1] call ACME_fnc_setVarNetApprox;
};
