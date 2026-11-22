/*
 * Can this rescuer drag this thing or this casualty behind them (ACME drag)?
 * The rescuer: on foot, awake, hands free (not dragging already, not on a litter handle).
 * The target: on the ground, not attached to anything, not claimed by anyone. A person has to be dead or not
 * awake, and not strapped into a litter (drag the litter). A thing must not be heavier than the setting, and
 * a litter must not have anybody on its handles.
 * Arguments: 0: rescuer, 1: target. Returns: bool.
 */
params ["_unit", "_target"];
alive _unit && {!isNull _target} && {_target isNotEqualTo _unit}
&& {isNull objectParent _unit} && {!(_unit getVariable ["ACE_isUnconscious", false])}
&& {isNull (_unit getVariable ["acme_drag_target", objNull])}
&& {!(_unit getVariable ["ace_dragging_isDragging", false])} && {!(_unit getVariable ["ace_dragging_isCarrying", false])}
&& {isNull (_unit getVariable ["acme_sked_bearing", objNull])}
&& {isNull objectParent _target} && {isNull attachedTo _target}
&& {isNull (_target getVariable ["acme_drag_by", objNull])}
&& {isNull (_target getVariable ["ace_common_owner", objNull])}
&& {!(_target getVariable ["acme_talon_busy", false])}
&& {
    if (_target isKindOf "CAManBase") then {
        isNull (_target getVariable ["acme_sked_litter", objNull])
        && {!(_target getVariable ["acme_sked_stowed", false])}
        && {!alive _target || {!(lifeState _target in ["HEALTHY", "INJURED"])}}
    } else {
        alive _target
        // A medical chest only while it is shut: open, its drawer unit, lid and hidden cargo are separate
        // things that would be left behind. (A shut chest that was moved seats itself where it is put down:
        // acm_extended, fn_medicalChestInit.sqf.)
        && {!(_target isKindOf "ACME_MedicalChestCargo")}
        && {
            !(_target isKindOf "ACME_MedicalChestVisual") || {
                _target isKindOf "ACME_MedicalChest"
                && {!((_target getVariable ["ACME_medicalChestState", [0, false]]) param [1, false])}
                && {!(_target getVariable ["ACME_medicalChestTransition", false])}
            }
        }
        // not a monitor on its mount, and no device that is being worked on
        && {!(_target getVariable ["ACME_eq_mounted", false])} && {!(_target getVariable ["ACME_eq_busy", false])}
        && {((_target getVariable ["acme_sked_bearers", []]) findIf {!isNull _x}) < 0}
        && {!(_target getVariable ["acme_sked_lifted", false])}
        && {(crew _target) isEqualTo []}
        && {(getMass _target) <= (missionNamespace getVariable ["acme_drag_maxMass", 1500])}
        // a litter that is taken by its handles (the Talon) is taken at its head end: he has to stand there
        && {
            getNumber (configOf _target >> "acmeDragLift") <= 0 || {
                private _handles = (getArray (configOf _target >> "acmeLitterHandles")) apply {_target modelToWorld (_target selectionPosition [_x, "Memory"])};
                count _handles < 4 || {
                    (_unit distance2D (((_handles select 0) vectorAdd (_handles select 1)) vectorMultiply 0.5))
                        < ((_unit distance2D (((_handles select 2) vectorAdd (_handles select 3)) vectorMultiply 0.5)) min 2.2)
                }
            }
        }
    }
}
