/*
 * Self action: has the player got a SKED, and are they on foot?
 * Arguments: 0: player. Returns: bool.
 */
params ["_player"];
"ACME_SKED_Item" in (items _player) && {isNull objectParent _player}
