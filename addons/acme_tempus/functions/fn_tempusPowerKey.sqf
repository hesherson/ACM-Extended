/* Hold the physical membrane key for 2.5 seconds. Releasing/leaving the view cancels it. */
params ["_key", "_button", "_pressed", ["_ls", false]];
if (_button != 0) exitWith {false};
private _generation = 1 + (_key getVariable ["ACME_power_hold", 0]);
_key setVariable ["ACME_power_hold", _generation];
if (!_pressed) exitWith {false};
private _device = _key getVariable ["ACME_power_device", objNull];
[{
    params ["_key", "_device", "_generation", "_ls"];
    if (isNull _key || {isNull _device} || {(_key getVariable ["ACME_power_hold", -1]) != _generation}) exitWith {};
    private _provider = call ACME_fnc_controlledProvider;
    if (isNull _provider || {!([_provider] call ace_common_fnc_isAwake)} || {_provider distance _device > 3.5}) exitWith {};
    private _name = ["acme_tempus_pw", "acme_tempusls_pw"] select _ls;
    private _on = !((_device getVariable [_name, [false]]) select 0);
    if (_ls) then {[_device, _on] call ACME_fnc_tempusLsPower;} else {[_device, _on] call ACME_fnc_tempusPower;};
    _key setVariable ["ACME_power_hold", _generation + 1];
}, [_key, _device, _generation, _ls], 2.5] call CBA_fnc_waitAndExecute;
false
