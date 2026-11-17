// A handle claim leaves both the provider's movement and camera under player control.
params ["_unit", "_litter", "_mode"];
if (!local _unit) exitWith {};
if !((_unit getVariable ["acme_sked_bearing", objNull]) isEqualTo _litter) exitWith {};
if (_mode == "lead" && {currentWeapon _unit != ""}) then {_unit action ["SwitchWeapon", _unit, _unit, 299]};
[_unit, "forceWalk", "acme_sked", _mode == "lead"] call ace_common_fnc_statusEffect_set;
if ((_unit getVariable ["acme_sked_bearerWatch", -1]) >= 0) exitWith {};
private _watch = [{
    params ["_args", "_id"];
    _args params ["_unit", "_litter"];
    if (!local _unit || {!alive _unit} || {isNull _litter} || {!((_unit getVariable ["acme_sked_bearing", objNull]) isEqualTo _litter)}) exitWith {
        [_id] call CBA_fnc_removePerFrameHandler;
        _unit setVariable ["acme_sked_bearerWatch", nil];
    };
    if (_unit distance _litter > 3.5) then {[_unit, "letGo"] call acme_sked_fnc_request;};
}, 0.5, [_unit, _litter]] call CBA_fnc_addPerFrameHandler;
_unit setVariable ["acme_sked_bearerWatch", _watch];
