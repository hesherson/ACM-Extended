/* Arrays/maps are reference containers in SQF. Freeze each message before a
 * synchronous local continuation can change its original clinical arguments. */
params ["_value"];
if (_value isEqualType []) exitWith {_value apply {[_x] call ACME_fnc_syringeDeliveryCopy}};
if (_value isEqualType createHashMap) exitWith {
    private _copy = createHashMap;
    {_copy set [_x,[(_value get _x)] call ACME_fnc_syringeDeliveryCopy];} forEach (keys _value);
    _copy
};
_value
