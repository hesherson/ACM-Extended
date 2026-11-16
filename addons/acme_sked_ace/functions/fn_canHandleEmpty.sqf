/*
 * Can the player handle an empty SKED or its pack (pick up, lay out, roll up)? Nobody is dragging,
 * carrying or holding it.
 * Arguments: 0: player, 1: object. Returns: bool.
 */
params ["_player", "_obj"];
alive _player
&& {isNull objectParent _player}
&& {isNull attachedTo _obj}
&& {isNull (_obj getVariable ["ace_common_owner", objNull])}
&& {isNull (_obj getVariable ["acme_sked_patient", objNull])}
