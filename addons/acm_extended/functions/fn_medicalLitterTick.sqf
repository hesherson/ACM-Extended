/* Finite local animation state machine. Completion requires observed authored moves, never just a timeout. */
params ["_args","_pfh"];
_args params ["_unit","_request","_token","_fingerprint","_origin","_stage","_stageAt","_seen","_deadline","_prepUntil","_minimumUntil",["_key",-1]];
private _retire = {[_pfh] call CBA_fnc_removePerFrameHandler;if (_key >= 0) then {(findDisplay 46) displayRemoveEventHandler ["KeyDown",_key];};};
if (isNull _unit) exitWith {call _retire;};
private _state = _unit getVariable ["ACME_litterCollect",[]];
if ((_state param [0,""]) != _request || {(_state param [1,""]) != _token}) exitWith {call _retire;};
private _current = [_unit getVariable ["ACME_providerLocalityEpoch",0],_unit getVariable ["ACME_treatmentPoseEpoch",0],_unit getVariable ["ACME_providerTreatmentEpoch",0]];
private _moving = ["MoveForward","MoveBack","MoveLeft","MoveRight","MoveFastForward","MoveSlowForward","TurnLeft","TurnRight"] findIf {inputAction _x > 0.05} >= 0;
if ((_state select 2) != "anim" || {diag_tickTime >= _deadline} || {_current isNotEqualTo _fingerprint}
    || {!([_unit,true] call ACME_fnc_medicalLitterCanCollect)}
    || {(getPosASL _unit) vectorDistance _origin > 0.5} || {_moving}) exitWith {
    [_unit,_request,_token,false,_current isEqualTo _fingerprint] call ACME_fnc_medicalLitterFinish;
};
private _now = diag_tickTime;
private _rest = "AmovPknlMstpSnonWnonDnon";
private _first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
private _second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";
private _anim = toLowerANSI animationState _unit;
private _neutral = _anim == toLowerANSI _rest || {(_anim find "aidlpknlmstpsnonwnondnon") == 0};
private _next = {params ["_stage",["_seen",false]];_args set [5,_stage];_args set [6,_now];_args set [7,_seen];};
if (_stage == 3) exitWith {
    // Respect the existing presentation-disabled setting without skipping the finite collection time.
    if (_now >= _minimumUntil) then {[_unit,_request,_token,true] call ACME_fnc_medicalLitterFinish;};
};
if !(missionNamespace getVariable ["ACME_interventionAnimations",true]) exitWith {[_unit,_request,_token,false] call ACME_fnc_medicalLitterFinish;};
if (_stage == -1) exitWith {
    if (_now < _prepUntil) exitWith {};
    // Wait for the actual empty-hands holster, rather than forcing a reach under a visible weapon.
    if (currentWeapon _unit != "" || {(_anim find "wpst") >= 0} || {(_anim find "wrfl") >= 0} || {(_anim find "wlnr") >= 0}) exitWith {};
    _unit setUnitPos "MIDDLE";
    [_unit,_rest,2] call ACME_fnc_doAnim;
    [0] call _next;
};
if (_stage == 0) exitWith {
    if (!_neutral || {_now - _stageAt < 0.15}) exitWith {};
    [_unit,_first,2] call ACME_fnc_doAnim;
    [1] call _next;
};
if (_stage == 1) exitWith {
    if (_anim == toLowerANSI _first) then {_args set [7,true];};
    if (_anim == toLowerANSI _second && {_seen}) exitWith {[2,true] call _next;};
    if (_seen && {_anim != toLowerANSI _first}) then {
        // BI may expose the authored middle Putdown state before its return transition.
        if (!_neutral && {_anim != "ainvpknlmstpsnonwnondnon_putdown"}) exitWith {[_unit,_request,_token,false] call ACME_fnc_medicalLitterFinish;};
        [_unit,_second,2] call ACME_fnc_doAnim;
        [2] call _next;
    };
};
if (_stage == 2) exitWith {
    if (_anim == toLowerANSI _second) then {_args set [7,true];};
    if (_seen && {_neutral}) then {[4] call _next;};
};
if (_stage == 4 && {_neutral} && {_now >= _minimumUntil}) then {
    [_unit,_request,_token,true] call ACME_fnc_medicalLitterFinish;
};
