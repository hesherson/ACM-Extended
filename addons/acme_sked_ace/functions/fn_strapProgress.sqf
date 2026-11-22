/*
 * ACE treatment callback, every frame of the timer: the medic's animation is kept going (fn_strapAnim.sqf).
 * Arguments: 0: the arguments of the treatment (0: medic, ...). Returns: true (the treatment goes on).
 */
params ["_args"];
_args params ["_medic"];
[_medic] call acme_sked_fnc_strapAnim;
true
