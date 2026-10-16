/* Atomic owner-side catheter removal and dependent equipment teardown. */
params ["_patient","_medic","_uid","_epoch"];
if (isNull _patient || {!local _patient} || {isNull _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_epoch!=([_patient] call ACME_fnc_clinicalEpoch)}
    || {([_medic,_patient] call ACME_fnc_patientInteractionDistance)>3}
    || {(objectParent _medic) isNotEqualTo (objectParent _patient)} || {_uid==""}) exitWith {false};
private _marks=_patient getVariable ["ACME_IV_Marks",[]];
private _i=_marks findIf {(_x param [14,""])==_uid && {(_x param [4,""])=="hub"}};
if (_i<0) exitWith {false};
private _row=+(_marks select _i);
private _raw=_row select 0;private _part=if (toLowerANSI _raw=="ej") then {"head"} else {toLowerANSI _raw};
private _site=[_row select 10] call ACME_fnc_ivSiteIndex;
isNil {
    [_patient,_part,_site] call ACME_fnc_ivAccessoryUnplug;
    [_medic,_patient,_part,0,true,_site,_epoch] call ACM_circulation_fnc_setIVLocal;
    private _sig=[_raw,_row select 1,_row select 2,_row select 3,_row select 10,_row select 7];
    [_patient,"remove",[_sig,format ["\acm_extended\ui\holes\hole%1_ca.paa",1+floor random 8]],_epoch] call ACME_fnc_ivMarkCommit;
    _patient setVariable [format ["ACME_ivCompromised_%1_%2",_part,_site],nil,true];
};
[_patient,"activity","%1 removed IV, %2",[[_medic,false,true] call ace_common_fnc_getName,[_raw,_row select 10] call ACME_fnc_ivLogSite]] call ace_medical_treatment_fnc_addToLog;
true
