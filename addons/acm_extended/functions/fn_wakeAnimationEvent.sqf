/* Called on the patient owner after the actual ACE unconsciousness edge. This is visual only.
 * Duplicate wake notifications cannot replay a clip; clinical wake is never deferred for presentation. */
params [["_patient",objNull,[objNull]], ["_unconscious",true,[false]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _fractures = _patient getVariable ["ace_medical_fractures",[0,0,0,0,0,0]];
private _acmFractures = _patient getVariable ["ACM_disability_Fracture_State",[0,0,0,0,0,0]];
private _arms = (_patient getVariable ["ACME_wakeHadArmFracture",false])
    || {(_fractures param [2,0]) != 0} || {(_fractures param [3,0]) != 0}
    || {(_acmFractures param [2,0]) != 0} || {(_acmFractures param [3,0]) != 0};
private _tbiState = _patient getVariable ["ACME_tbi_State",createHashMap];
private _tbi = (_patient getVariable ["ACME_wakeHadTBI",false])
    || {_patient getVariable ["ACME_tbi_HasTBI",false]}
    || {(_tbiState getOrDefault ["severity",0]) > 0}
    || {(_tbiState getOrDefault ["structuralSeverity",0]) > 0};
// 0.5 normalized body damage is a presentation threshold, not a new clinical injury rule.
private _torso = (_patient getVariable ["ACME_wakeHadTorsoDamage",false])
    || {((_patient getVariable ["ace_medical_bodyPartDamage",[]]) param [1,0]) >= 0.5};
{_patient setVariable [_x select 0, _x select 1, true];} forEach [
    ["ACME_wakeHadArmFracture",_arms], ["ACME_wakeHadTBI",_tbi], ["ACME_wakeHadTorsoDamage",_torso]
];
if (_unconscious) exitWith {
    [_patient] call ACME_fnc_wakeAnimationStop;
    _patient setVariable ["ACME_wakeVisualArmed",true,true];
    true
};
if (!(_patient getVariable ["ACME_wakeVisualArmed",false])) exitWith {false};
_patient setVariable ["ACME_wakeVisualArmed",false,true];
[_patient] call ACME_fnc_wakeAnimationStop;
if (!alive _patient || {_patient getVariable ["ACE_isUnconscious",false]}
    || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
    || {_patient getVariable ["ACME_roc_paralyzed",false]}) exitWith {false};
// B225: actual waking (including spontaneous/Zeus wake) always keeps the medical
// lying contract. This is not Get Up, even when a native wake path cleared its flag.
[_patient, true, true] call ACM_core_fnc_setLyingState;
private _serial = (_patient getVariable ["ACME_wakeVisualSerial",0]) + 1;
_patient setVariable ["ACME_wakeVisualSerial",_serial,true];
private _move = [_tbi,_arms,_torso] call ACME_fnc_wakeAnimationChoice;
private _rest = "ACM_LyingState";
private _duration = [_move] call ACME_fnc_nativeAnimationTime;
// Missing/disabled native animation is not a reason to immobilize a medically awake patient.
if (_duration <= 0 || {_duration > 30}) exitWith {false};
private _record = [_serial,_move,_rest,0,CBA_missionTime,CBA_missionTime+1.5,
    [_patient] call ACME_fnc_clinicalEpoch,-1,getPosWorld _patient,-1,_duration,false];
_patient setVariable ["ACME_wakeVisual",_record,false];
_patient setVariable ["ACME_wakeVisualToken",[_serial,serverTime+_duration+3],true];
private _pfh = [{_this call ACME_fnc_wakeAnimationTick;},0.05,[_patient,_serial]] call CBA_fnc_addPerFrameHandler;
_record set [7,_pfh];
true
