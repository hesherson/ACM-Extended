/*
 * Can this unit be strapped into a SKED? On foot, not attached to anything (not dragged, carried or
 * escorted), not already in a SKED, not claimed by someone; dead, or not awake (or awake if the
 * setting allows it).
 * Arguments: 0: unit. Returns: bool.
 */
params ["_unit"];
!isNull _unit
&& {isNull objectParent _unit}
&& {isNull attachedTo _unit || {(_unit getVariable ["ACME_headElevated", false])
    && {(attachedTo _unit) isEqualTo (_unit getVariable ["ACME_headElev_helper", objNull])}}
    // being laid on a litter while the timer of the strap action runs
    || {(attachedTo _unit) isEqualTo (_unit getVariable ["acme_sked_placing", objNull])}}
&& {isNull (_unit getVariable ["acme_sked_litter", objNull])}
&& {!(_unit getVariable ["acme_sked_stowed", false])}
&& {isNull (_unit getVariable ["ace_common_owner", objNull])}
&& {!alive _unit || {!(lifeState _unit in ["HEALTHY", "INJURED"])} || {missionNamespace getVariable ["acme_sked_allowConscious", false]}}
