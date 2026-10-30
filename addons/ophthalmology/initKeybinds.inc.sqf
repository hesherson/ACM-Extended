#include "\a3\ui_f\hpp\defineDIKCodes.inc"

if (!hasInterface) exitWith {};

[CBA_SETTINGS_CAT, QGVAR(blinking), LLSTRING(blink_action),
{
    if !(missionNamespace getVariable [QGVAR(enable), false]) exitWith {};
    if (isNull ACE_player || {!local ACE_player} || {!alive ACE_player}
        || {ACE_player getVariable ["ACE_isUnconscious",false]}) exitWith {};

    [0.2, false] call FUNC(effectEyeBlink);

    private _random = floor(random 100);

    if (_random <= GVAR(probability_treatment_dust)) then {
        private _dustInjuryLight = ACE_player getVariable [QGVAR(dustInjuryLight), 0];
        ACE_player setVariable [QGVAR(dustInjuryLight), ((_dustInjuryLight - 0.5) max 0), true];
    };
}, "",
[DIK_F, [true, true, false]], false] call CBA_fnc_addKeybind;
// [DIK, [shift, ctrl, alt]]
