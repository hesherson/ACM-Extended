[QGVAR(setHidden), {
    params ["_object", "_set"];
    TRACE_2("setHidden EH",_object,_set);
    // May report nil. Default to factor 1.
    private _vis = [_object getUnitTrait "camouflageCoef"] param [0, 1];
    if (_set > 0) then {
        if (_vis != 0) then {
            _object setVariable [QGVAR(oldVisibility), _vis];
            _object setUnitTrait ["camouflageCoef", 0];
            {
                if (side _x != side group _object) then {
                    _x forgetTarget _object;
                };
            } forEach allGroups;
        };
    } else {
        _vis = _object getVariable [QGVAR(oldVisibility), _vis];
        _object setUnitTrait ["camouflageCoef", _vis];
    };
}] call CBA_fnc_addEventHandler;
