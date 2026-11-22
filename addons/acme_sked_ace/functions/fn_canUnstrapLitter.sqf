/*
 * Can the casualty be taken out of this SKED? It is on the ground, nobody drags or carries it, and
 * nobody holds a handle.
 * Arguments: 0: player, 1: SKED. Returns: bool.
 */
params ["_player", "_litter"];
!isNull _litter
&& {!isNull (_litter getVariable ["acme_sked_patient", objNull])}
// (free, or dragged by this very rescuer: he lets go as he begins, see fn_loadVehicle.sqf and fn_unstrapLitter.sqf)
&& {(_litter getVariable ["acme_drag_by", objNull]) isEqualTo _player
    || {isNull attachedTo _litter && {isNull (_litter getVariable ["ace_common_owner", objNull])}}}
&& {!(_litter getVariable ["acme_sked_lifted", false])}
&& {((_litter getVariable ["acme_sked_bearers", []]) findIf {!isNull _x}) < 0}
