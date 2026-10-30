#include "..\script_component.hpp"
/*
 * Author: Inferno
 * Keep local ophthalmology visual effects synchronized with player state.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Public: No
 */

private _player = missionNamespace getVariable ["ACE_player", objNull];
if (!(_player isEqualTo (missionNamespace getVariable [QGVAR(visualPlayer),objNull]))) then {
    GVAR(visualPlayer) = _player;
    [] call FUNC(resetVisualEffects);
};

if (
    isNull _player ||
    {!alive _player} ||
    {missionNamespace getVariable [QACEGVAR(common,OldIsCamera), false]} ||
    {_player getVariable ["ACE_isUnconscious", false]}
) exitWith {
    [] call FUNC(resetVisualEffects);
};

private _dustInjurySeverity = GET_DUST_INJURY(_player);
private _eyeInjuries = _player getVariable [QGVAR(eyeInjuries), [1, 1]];

[true, _dustInjurySeverity] call FUNC(effectEyeInjury);
[true, _eyeInjuries] call FUNC(effectHurtEye);

private _shieldItem = _player getVariable [QGVAR(eyeShieldItem),""];
private _shieldIndex = _player getVariable [QGVAR(eyeShieldIndex),-1];
if (_shieldIndex in [0,1]
    && {_shieldItem == (["kat_eyecovers_right","kat_eyecovers_left"] select _shieldIndex)}
    && {(hmd _player) == _shieldItem}) then {
    [([17102,17103] select _shieldIndex)] call FUNC(showEyeShieldOverlay);
} else {
    [] call FUNC(hideEyeShieldOverlay);
};
