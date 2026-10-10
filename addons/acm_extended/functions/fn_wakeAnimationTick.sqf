/* Finite wake clip observer. No looping, frozen frames, global input lock or repeated pose asserts. */
params ["_args","_pfh"];
_args params ["_patient","_serial"];
if (isNull _patient) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _record = _patient getVariable ["ACME_wakeVisual",[]];
if (count _record < 12 || {(_record select 0) != _serial} || {(_record select 7) != _pfh}) exitWith {
    [_pfh] call CBA_fnc_removePerFrameHandler;
};
if (!local _patient || {!alive _patient} || {_patient getVariable ["ACE_isUnconscious",false]}
    || {(_record select 6) != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
    || {_patient call ace_common_fnc_isBeingDragged} || {_patient call ace_common_fnc_isBeingCarried}) exitWith {
    [_patient,_serial] call ACME_fnc_wakeAnimationStop;
};
private _phase = _record select 3;
private _otherPose = ((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime
    || {_patient getVariable ["ACME_headElevated",false]}
    || {_patient getVariable ["ACM_airway_RecoveryPosition_State",false]}
    || {_patient getVariable ["ACME_roc_paralyzed",false]}
    || {(_patient getVariable ["ACME_lido_seizureState",""]) == "active"};
private _moveInput = false;
if (hasInterface && {_patient isEqualTo ACE_player}) then {
    _moveInput = ["MoveForward","MoveBack","MoveLeft","MoveRight","MoveFastForward","MoveSlowForward","Evasive"]
        findIf {(inputAction _x) > 0.01} >= 0;
};
private _released = (_record select 2) == "ACM_LyingState" && {!(_patient getVariable ["ACM_core_Lying_State",false])};
if (_moveInput || {_released} || {(_patient distance2D (_record select 8)) > 0.35}) exitWith {
    [_patient,_serial,true] call ACME_fnc_wakeAnimationStop;
};
if (_otherPose && {_phase != 0}) exitWith {[_patient,_serial] call ACME_fnc_wakeAnimationStop;};
if (CBA_missionTime > (_record select 5)) exitWith {[_patient,_serial,true] call ACME_fnc_wakeAnimationStop;};
private _move = _record select 1;
private _current = toLowerANSI animationState _patient;
if (_phase == 0) exitWith {
    // Give outgoing unconscious/chest controllers a bounded moment to relinquish their leases.
    if (!_otherPose && {lifeState _patient != "INCAPACITATED"} && {abs (getAnimSpeedCoef _patient - 1) < 0.01}) then {
        _record set [3,1]; _record set [9,CBA_missionTime];
        _patient playMoveNow _move;
    };
};
if (_current == toLowerANSI _move) then {
    if (_phase == 1) then {
        _record set [3,2];
        _record set [5,CBA_missionTime+(_record select 10)+0.5];
    };
    if ((_patient getUnitMovesInfo 0) >= 0.98) then {[_patient,_serial,true] call ACME_fnc_wakeAnimationStop;};
} else {
    if (_phase == 2) exitWith {
        // Natural graph completion OR another action won. Never put the old clip back.
        [_patient,_serial] call ACME_fnc_wakeAnimationStop;
    };
    // ACM_LyingState is intentionally isolated. Try one partial-blend entry only from the
    // unchanged resting pose; an intervening treatment/Get Up may never be overwritten.
    if (!(_record select 11) && {CBA_missionTime-(_record select 9) >= 0.25}
        && {_current == toLowerANSI (_record select 2)}) then {
        _record set [11,true];
        _patient switchMove [_move,0,0.25,false];
    };
};
