// This also accepts a native loadout array or a saved ACME snapshot.
if (_this isEqualType "") exitWith {[_this] call ACME_fnc_itemClassCanonical};
if (_this isEqualType []) exitWith {_this apply {_x call ACME_fnc_itemDataCanonical}};
if (_this isEqualType createHashMap) exitWith {
    private _copy = createHashMap;
    {_copy set [_x, _y call ACME_fnc_itemDataCanonical];} forEach _this;
    _copy
};
_this
