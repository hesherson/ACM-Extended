/* Versioned persistence boundary. Validate every record before inventory/cargo changes. */
params ["_snapshot"];
if (isNil "_snapshot") exitWith {false};
if !(_snapshot isEqualType [] && {count _snapshot == 3}) exitWith {false};
if (([0,1,2] findIf {isNil {_snapshot select _x}}) >= 0) exitWith {false};
if ((_snapshot select 0) isNotEqualTo 1 || {!((_snapshot select 1) in ["holder","box"])}) exitWith {false};
private _rows = _snapshot select 2;
if !(_rows isEqualType [] && {count _rows <= 128}) exitWith {false};
private _box = (_snapshot select 1) == "box";
if (_box && {count _rows != 1}) exitWith {false};
private _ids = createHashMap;
private _tokens = createHashMap;
private _validRow = {
    params ["_row"];
    if (isNil "_row") exitWith {false};
    if !(_row isEqualType [] && {count _row == 5}) exitWith {false};
    if (([0,1,2,3,4] findIf {isNil {_row select _x}}) >= 0) exitWith {false};
    _row params ["_sid","_token","_base","_age","_entries"];
    if !(_sid isEqualType "" && {count _sid > 0} && {count _sid <= 256}
        && {_token isEqualType 0} && {finite _token} && {_token == floor _token}
        && {_base isEqualType ""} && {_age isEqualType 0} && {finite _age} && {_age >= 0}
        && {_entries isEqualType []} && {count _entries <= 8}) exitWith {false};
    if (_sid in _ids || {!_box && {str _token in _tokens}}) exitWith {false};
    if ((_box && {_token != 0}) || {!_box && {(_token <= 0 || {_token >= 65535})}}) exitWith {false};
    private _index = ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"] find _base;
    if (_index < 0) exitWith {false};
    private _ml = 0;
    private _validBag = {
        params ["_entry"];
        if (isNil "_entry") exitWith {false};
        if !(_entry isEqualType [] && {count _entry == 2}) exitWith {false};
        if (isNil {_entry select 0} || {isNil {_entry select 1}}) exitWith {false};
        _entry params ["_bag","_warm"];
        if !(_bag isEqualType "" && {count _bag <= 128} && {_warm isEqualType 0} && {finite _warm} && {_warm >= 0}) exitWith {false};
        if !((_bag find "ACM_BloodBag_") == 0 || {(_bag find "ACM_FreshBloodBag_") == 0}) exitWith {false};
        if !(isClass (configFile >> "CfgWeapons" >> _bag)) exitWith {false};
        private _volume = 0;
        private _parts = _bag splitString "_";
        private _suffix = _parts select ((count _parts) - 1);
        {if (_suffix == str _x) exitWith {_volume = _x;};} forEach [1000,500,250];
        _ml = _ml + _volume;
        _volume > 0
    };
    private _bagsOK = true;
    {if !([_x] call _validBag) exitWith {_bagsOK = false;};} forEach _entries;
    if (!_bagsOK || {_ml > ([500,1000,2000] select _index)}) exitWith {false};
    _ids set [_sid,true];
    _tokens set [str _token,true];
    true
};
private _valid = true;
{if !([_x] call _validRow) exitWith {_valid = false;};} forEach _rows;
_valid
