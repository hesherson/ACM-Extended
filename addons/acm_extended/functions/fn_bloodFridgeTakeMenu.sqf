// the insertchildren for the "Take Blood Unit" ACE action. it builds one child per in-stock blood type, labeled
// with the remaining count. it reads the broadcast stock off the anchor, which works from either the closed or
// the open model.
// _this is [_target, _player, _params].
params ["_target"];
private _anchor = _target getVariable ["ACME_bf_anchor", _target];
if (isNull _anchor) exitWith { [] };

private _stock = _anchor getVariable ["ACME_bf_stock", []];
private _actions = [];
{
    _x params ["_class", "_count"];
    if (_count > 0) then {
        private _cfg = configFile >> "CfgWeapons" >> _class;
        private _name = getText (_cfg >> "displayName");
        private _icon = getText (_cfg >> "picture");
        private _act = [
            format ["ACME_bfTake_%1", _class],
            format ["%1  -  %2 left", _name, _count],
            _icon,
            {
                params ["_t", "_player", "_args"];
                _args params ["_anchor", "_class"];
                [_anchor, _class, _player] call ACME_fnc_bloodFridgeTake;
            },
            {params ["_target", "_player"]; (_player getVariable ["ACME_bf_take", []]) isEqualTo []},
            {},
            [_anchor, _class]
        ] call ace_interact_menu_fnc_createAction;
        _actions pushBack [_act, [], _target];
    };
} forEach _stock;

_actions
