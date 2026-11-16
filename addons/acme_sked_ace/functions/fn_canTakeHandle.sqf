/*
 * SKED action: can the player take a handle? A casualty is strapped in, the SKED is on the ground and not
 * being dragged, a handle is free, and the player is on foot and not already holding one.
 * Arguments: 0: player, 1: SKED. Returns: bool.
 */
params ["_player", "_litter"];
private _bearers = _litter getVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull]];
!isNull (_litter getVariable ["acme_sked_patient", objNull])
&& {isNull attachedTo _litter}
&& {isNull (_litter getVariable ["ace_common_owner", objNull])}
&& {!(_litter getVariable ["acme_sked_lifted", false])}
&& {isNull (_player getVariable ["acme_sked_bearing", objNull])}
&& {isNull objectParent _player}
&& {({!isNull _x} count _bearers) < (([_litter] call acme_sked_fnc_bearerLimits) select 1)}
