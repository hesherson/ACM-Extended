/*
 * Can this rescuer lift the foot end of this litter? The litter is one that is taken by its handles (the Talon),
 * another rescuer drags it by its head end, nobody has the foot end yet, and this rescuer is on foot, awake,
 * near it and has his hands free.
 * Arguments: 0: rescuer, 1: litter. Returns: bool.
 */
params ["_unit", "_litter"];
alive _unit && {!isNull _litter} && {isNull objectParent _unit} && {!(_unit getVariable ["ACE_isUnconscious", false])}
&& {getNumber (configOf _litter >> "acmeDragLift") > 0}
// He has to stand at its foot end: no further from the first rescuer than the two belong apart and 0.8 m
// (at 0.9 m he would be let go again as torn apart). Measured against the first rescuer, whose place every
// machine knows: the server can hold a litter that hangs on another machine's rescuer a second or two behind.
&& {
    private _lead = _litter getVariable ["acme_drag_by", objNull];
    !isNull _lead && {_lead isNotEqualTo _unit} && {_unit distance2D _lead < (_litter getVariable ["acme_carry_span", 3]) + 0.8}
}
&& {isNull (_litter getVariable ["acme_carry_rear", objNull])}
&& {isNull (_unit getVariable ["acme_carry_litter", objNull])}
&& {isNull (_unit getVariable ["acme_drag_target", objNull])}
&& {isNull (_unit getVariable ["acme_sked_bearing", objNull])}
&& {!(_unit getVariable ["ace_dragging_isDragging", false])} && {!(_unit getVariable ["ace_dragging_isCarrying", false])}
