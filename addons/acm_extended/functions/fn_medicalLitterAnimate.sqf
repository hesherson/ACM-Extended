/* Kneel, then the exact provider Putdown reach/return used by Semi-Fowler's. No patient posture is involved. */
params ["_unit","_request","_token"];
if !([_unit,true] call ACME_fnc_medicalLitterCanCollect) exitWith {[_unit,_request,_token,false] call ACME_fnc_medicalLitterFinish;};
private _state = _unit getVariable ["ACME_litterCollect",[]];
if ((_state param [0,""]) != _request || {(_state param [1,""]) != _token} || {(_state param [2,""]) != "request"}) exitWith {};
_state set [2,"anim"];
private _fingerprint = [_unit getVariable ["ACME_providerLocalityEpoch",0],_unit getVariable ["ACME_treatmentPoseEpoch",0],_unit getVariable ["ACME_providerTreatmentEpoch",0]];
private _enabled = missionNamespace getVariable ["ACME_interventionAnimations",true];
private _prep = if (_enabled) then {[_unit] call ACME_fnc_medicAnimationPrep} else {0};
private _now = diag_tickTime;
private _args = [_unit,_request,_token,_fingerprint,getPosASL _unit,if (_enabled) then {-1} else {3},_now,false,_now + 10,_now + ((_prep max 0) max 0.05),_now + 2.1];
private _key = (findDisplay 46) displayAddEventHandler ["KeyDown",{
    if ((_this select 1) == 1) then {
        private _actor = call ACME_fnc_controlledProvider;
        private _active = _actor getVariable ["ACME_litterCollect",[]];
        if ((_active param [2,""]) == "anim") then {_active set [2,"cancel"];};
    };
    false
}];
_unit setVariable ["ACME_litterKey",_key];
_args pushBack _key;
private _pfh = [{_this call ACME_fnc_medicalLitterTick;},0.05,_args] call CBA_fnc_addPerFrameHandler;
_unit setVariable ["ACME_litterPFH",_pfh];
