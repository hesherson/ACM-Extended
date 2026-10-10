#include "..\script_component.hpp"
/*
 * Author: commy2
 * Force local unit into ragdoll / unconsciousness animation.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: Is unconscious (optional, default: true) <BOOLEAN>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, true] call ace_medical_engine_fnc_setUnconsciousAnim
 *
 * Public: No
 */

params [["_unit", objNull, [objNull]], ["_isUnconscious", true, [false]]];
TRACE_2("setUnconsciousAnim",_unit,_isUnconscious);

if (!local _unit) exitWith {
    ERROR_1("Unit %1 not local or null",_unit);
};

// B225: retire old presentation/repair jobs before the native unconscious controller
// takes over. No forced ground/prone animation is introduced on the unconscious edge.
private _poseTicket = (_unit getVariable ["ACME_wakePoseTicket",0]) + 1;
_unit setVariable ["ACME_wakePoseTicket",_poseTicket,true];
if (_isUnconscious && {!isNil "ACME_fnc_wakeAnimationStop"}) then {
    [_unit] call ACME_fnc_wakeAnimationStop;
};
// ACE has already written its Boolean before calling this hook. Use the still-active
// engine state and the armed episode, not that now-cleared Boolean, to recognize wake.
private _medicalWake = !_isUnconscious && {!(_unit getVariable ["ACE_isUnconscious",false])}
    && {alive _unit} && {isNull objectParent _unit}
    && {isNull attachedTo _unit}
    && {(_unit getVariable ["ACME_wakeVisualArmed",false]) || {lifeState _unit == "INCAPACITATED"}};
if (_medicalWake) then {
    [_unit,true,true] call FUNC(setWasTreated);
    [_unit,true,true] call FUNC(setLyingState);
};
_unit setUnconscious _isUnconscious;

if (_isUnconscious) then {
    // eject from static weapon
    if (vehicle _unit isKindOf "StaticWeapon" && {!(vehicle _unit isKindOf "Pod_Heli_Transport_04_crewed_base_F")}) then {
        TRACE_2("ejecting from static weapon",_unit,vehicle _unit);
        [_unit] call ACEFUNC(common,unloadPerson);
    };

    // set animation inside vehicles
    if (!isNull objectParent _unit) then {
        private _unconAnim = _unit call ACEFUNC(common,getDeathAnim);
        TRACE_2("inVehicle - playing death anim",_unit,_unconAnim);
        [_unit, _unconAnim] call ACEFUNC(common,doAnimation);
    };
} else {
    // reset animation inside vehicles
    if (!isNull objectParent _unit) then {
        private _awakeAnim = _unit call ACEFUNC(common,getAwakeAnim);
        TRACE_2("inVehicle - playing awake anim",_unit,_awakeAnim);
        [_unit, _awakeAnim, 2] call ACEFUNC(common,doAnimation);
    } else {
        // and on foot
        TRACE_1("onfoot - playing standard anim",_unit);

        if (_unit getVariable [QGVAR(WasTreated), false] || _unit getVariable [QGVAR(Lying_State), false]) then {
            [QACEGVAR(common,switchMove), [_unit, "ACM_LyingState"]] call CBA_fnc_globalEvent;

            [{
                params ["_unit","_poseTicket"];
                if (!alive _unit || {!local _unit} || {_unit getVariable ["ACE_isUnconscious",false]}
                    || {(_unit getVariable ["ACME_wakePoseTicket",-1]) != _poseTicket}
                    || {!(_unit getVariable [QGVAR(Lying_State),false])}
                    || {!isNull objectParent _unit} || {!isNull attachedTo _unit}
                    || {((_unit getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}
                    || {_unit getVariable ["ACME_headElevated",false]}
                    || {_unit getVariable ["ACM_airway_RecoveryPosition_State",false]}) exitWith {};
                // Fix unit being in locked animation with switchMove (If unit was unloaded from a vehicle, they may be in deadstate instead of unconscious)
                private _animation = animationState _unit;
                if ((_animation == "unconscious" || {_animation == "deadstate" || {_animation find QACEGVAR(medical_engine,uncon_anim) != -1}}) && {lifeState _unit != "INCAPACITATED"}) then {
                    [QACEGVAR(common,switchMove), [_unit, "ACM_LyingState"]] call CBA_fnc_globalEvent;
                };
            }, [_unit,_poseTicket], 0.5] call CBA_fnc_waitAndExecute;
        } else {
            if (animationState _unit in LYING_ANIMATION) then {
                [_unit, "UnconsciousOutProne", 2] call ACEFUNC(common,doAnimation); // Roll out
            } else {
                [_unit, "AmovPpneMstpSnonWnonDnon", 2] call ACEFUNC(common,doAnimation);

                [{
                    params ["_unit","_poseTicket"];
                    TRACE_3("after delay",_unit,animationState _unit,lifeState _unit);
                    if (!alive _unit || {!local _unit} || {_unit getVariable ["ACE_isUnconscious",false]}
                        || {(_unit getVariable ["ACME_wakePoseTicket",-1]) != _poseTicket}
                        || {_unit getVariable [QGVAR(Lying_State),false]}
                        || {!isNull objectParent _unit} || {!isNull attachedTo _unit}
                        || {((_unit getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}
                        || {_unit getVariable ["ACME_headElevated",false]}
                        || {_unit getVariable ["ACM_airway_RecoveryPosition_State",false]}) exitWith {};
                    // Fix unit being in locked animation with switchMove (If unit was unloaded from a vehicle, they may be in deadstate instead of unconscious)
                    private _animation = animationState _unit;
                    if ((_animation == "unconscious" || {_animation == "deadstate" || {_animation find QACEGVAR(medical_engine,uncon_anim) != -1}}) && {lifeState _unit != "INCAPACITATED"}) then {
                        [_unit, "AmovPpneMstpSnonWnonDnon", 2] call ACEFUNC(common,doAnimation);
                        TRACE_1("forcing SwitchMove",animationState _unit);
                    };
                }, [_unit,_poseTicket], 0.5] call CBA_fnc_waitAndExecute;
            };
        };
    };
};
