/*
 * Self action: can this rescuer lift the SKED? Enough rescuers stand at a handle (setting), it is on the
 * ground and not being dragged. The one who lifts leads: they walk, the others follow.
 * Arguments: 0: player. Returns: bool.
 */
params ["_player"];
private _litter = _player getVariable ["acme_sked_bearing", objNull];
!isNull _litter
&& {!(_litter getVariable ["acme_sked_lifted", false])}
&& {isNull attachedTo _litter}
&& {isNull (_litter getVariable ["ace_common_owner", objNull])}
&& {({!isNull _x && {alive _x} && {(attachedTo _x) isEqualTo _litter}} count (_litter getVariable ["acme_sked_bearers", []])) >= (missionNamespace getVariable ["acme_sked_bearersRequired", 2])}
