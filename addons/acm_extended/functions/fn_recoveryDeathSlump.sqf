/* Brief owner-local ragdoll handoff damping, not a corpse pose controller.
   Remove only the artificial upward component of a near-stationary recovery casualty's death transition.
   Preserve horizontal motion, downward gravity, injury evidence, and genuine fast/airborne impulses. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {alive _patient}
    || {!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false])
        && {(toLowerANSI animationState _patient) != "acm_recoveryposition"}}
    || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
    || {_patient call ace_common_fnc_isBeingDragged}
    || {_patient call ace_common_fnc_isBeingCarried}) exitWith {false};
if ((_patient getVariable ["ACME_recoveryDeathDamp",[]]) isNotEqualTo []) exitWith {false};
private _vel = velocity _patient;
if (vectorMagnitude [_vel select 0,_vel select 1,0] > 2.5 || {abs (_vel select 2) > 6}
    || {((getPosATL _patient) select 2) > 1.2}) exitWith {false};
private _record = [[_patient] call ACME_fnc_clinicalEpoch,diag_tickTime,getPosASL _patient];
_patient setVariable ["ACME_recoveryDeathDamp",_record,false];
// An external postmortem hit cancels this cosmetic mitigation instead of swallowing its impulse.
private _hit = _patient addEventHandler ["Hit",{(_this select 0) setVariable ["ACME_recoveryDeathDamp",[],false];}];
[{
    params ["_args","_handle"];
    _args params ["_patient","_record","_hit"];
    private _stop = isNull _patient || {!local _patient} || {alive _patient}
        || {!((_patient getVariable ["ACME_recoveryDeathDamp",[]]) isEqualTo _record)}
        || {([_patient] call ACME_fnc_clinicalEpoch) != (_record select 0)}
        || {diag_tickTime >= (_record select 1) + 0.65}
        || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
        || {_patient call ace_common_fnc_isBeingDragged}
        || {_patient call ace_common_fnc_isBeingCarried};
    private _velocity = velocity _patient;
    if (!_stop) then {
        _stop = vectorMagnitude [_velocity select 0,_velocity select 1,0] > 2.5
            || {abs (_velocity select 2) > 6}
            || {(_patient distance2D (_record select 2)) > 0.75};
    };
    if (_stop) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient) then {
            _patient removeEventHandler ["Hit",_hit];
            if ((_patient getVariable ["ACME_recoveryDeathDamp",[]]) isEqualTo _record) then {
                _patient setVariable ["ACME_recoveryDeathDamp",[],false];
            };
        };
    };
    if ((_velocity select 2) > 0) then {
        _patient setVelocity [_velocity select 0,_velocity select 1,0];
    };
},0,[_patient,_record,_hit]] call CBA_fnc_addPerFrameHandler;
true
