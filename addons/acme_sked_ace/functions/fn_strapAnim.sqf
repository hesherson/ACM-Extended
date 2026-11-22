/*
 * Where the medic is local, every frame of a strap timer: his animation is kept going. The animation of a
 * treatment lasts five or six seconds and the timer ten; when it has run out he is given it again, after a
 * second's rest.
 * Arguments: 0: medic, 1: the animation <STRING> (default: the treatment animation he was seen in: ACE's
 * medical menu gave it to him and does not say which).
 */
params ["_medic", ["_move", ""]];
if (_move == "") then {
    if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith {};
    if ("medic" in toLowerANSI animationState _medic) then {_medic setVariable ["acme_strap_move", animationState _medic];};
    _move = _medic getVariable ["acme_strap_move", ""];
};
if (_move == "") exitWith {};
// in it (or in the engine's own variant of it): nothing to do
if ("medic" in toLowerANSI animationState _medic) exitWith {
    _medic setVariable ["acme_strap_animAt", CBA_missionTime];
    _medic setVariable ["acme_strap_animTries", nil];
};
if (CBA_missionTime - (_medic getVariable ["acme_strap_animAt", -10]) < 1) exitWith {};
_medic setVariable ["acme_strap_animAt", CBA_missionTime];
// Asked for the usual way first. From some stances the engine does not take that up (seen in game 2026-11-18:
// kneeling with the weapon raised, he stayed kneeling); a second later he is put into it directly.
private _tries = _medic getVariable ["acme_strap_animTries", 0];
_medic setVariable ["acme_strap_animTries", _tries + 1];
[_medic, _move, [1, 2] select (_tries > 0)] call ace_common_fnc_doAnimation;
