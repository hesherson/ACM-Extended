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
&& {_player distance _litter <= 3.5}
&& {({!isNull _x && {alive _x} && {!(_x getVariable ["ACE_isUnconscious", false])}
    && {isNull attachedTo _x} && {isNull objectParent _x} && {_x distance _litter <= 3.5}}
    count (_litter getVariable ["acme_sked_bearers", []])) >= (([_litter] call acme_sked_fnc_bearerLimits) select 0)}
