params ["_litter", "_player"];
([_litter, _player, true] call acme_sked_fnc_findCasualty) apply {
    private _name = format ["%1 (%2 m)", [_x, false, true] call ace_common_fnc_getName,
        (_player distance _x) toFixed 1];
    private _action = [str _x, _name, "", {
        params ["_target", "_player", "_patient"];
        [_player, _target, _patient] call acme_sked_fnc_strapNearest;
    }, {
        params ["_target", "_player", "_patient"];
        [_player, _target] call acme_sked_fnc_canHandleEmpty && {[_patient] call acme_sked_fnc_validCasualty}
    }, {}, _x] call ace_interact_menu_fnc_createAction;
    [_action, [], _litter]
}
