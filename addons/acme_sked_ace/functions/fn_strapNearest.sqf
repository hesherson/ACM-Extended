/*
 * SKED action: package the nearest casualty in this SKED.
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter", ["_patient", objNull]];
if (uiNamespace getVariable ["ace_interact_menu_cursorMenuOpened", false]) exitWith {
    [acme_sked_fnc_strapNearest, _this] call CBA_fnc_execNextFrame;
};
if (isNull _litter || {!([_player, _litter] call acme_sked_fnc_canHandleEmpty)}) exitWith {};
if (isNull _patient) then {_patient = [_litter, _player] call acme_sked_fnc_findCasualty;};
if (isNull _patient || {_player distance _patient > 3.5} || {_patient distance _litter > 3.5}
    || {!([_patient] call acme_sked_fnc_validCasualty)}) exitWith {};
private _move = "";
if (missionNamespace getVariable ["ACME_interventionAnimations", true]) then {
    private _pose = ["knl", "pne"] select (stance _player == "PRONE");
    private _weapons = ["", primaryWeapon _player, secondaryWeapon _player, handgunWeapon _player];
    private _weapon = ["non", "rfl", "lnr", "pst"] param [_weapons find currentWeapon _player, "non"];
    _move = format ["AinvP%1MstpSlayW%2Dnon_medicOther", _pose, _weapon];
    if (weaponLowered _player && {currentWeapon _player != ""}) then {_player action ["WeaponInHand", _player];};
    [_player, _move, 1] call ace_common_fnc_doAnimation;
};
private _finishMove = {
    params ["_player", "_move"];
    if (_move != "" && {alive _player} && {isNull objectParent _player}
        && {!(_player getVariable ["ACE_isUnconscious", false])}
        && {toLowerANSI animationState _player == toLowerANSI _move}) then {
        [_player, "", 2] call ace_common_fnc_doAnimation;
    };
};
[15, [_player, _patient, _litter, _move, _finishMove], {
    (_this select 0) params ["_player", "_patient", "_litter", "_move", "_finishMove"];
    [_player, _move] call _finishMove;
    [_player, "strap", _patient, _litter] call acme_sked_fnc_request;
}, {
    (_this select 0) params ["_player", "", "", "_move", "_finishMove"];
    [_player, _move] call _finishMove;
}, "Packaging casualty in litter...", {
    (_this select 0) params ["_player", "_patient", "_litter"];
    !isNull _litter && {[_player, _litter] call acme_sked_fnc_canHandleEmpty}
        && {_player distance _patient <= 3.5} && {_patient distance _litter <= 3.5}
        && {[_patient] call acme_sked_fnc_validCasualty}
}] call ace_common_fnc_progressBar;
