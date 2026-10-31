/* JSON-safe prepared equipment schema. Validate the complete import before funding. */
params ["_snapshot"];
if (isNil "_snapshot" || {!(_snapshot isEqualType [])} || {count _snapshot != 2}) exitWith {false};
if (isNil {_snapshot select 0} || {isNil {_snapshot select 1}}) exitWith {false};
if ((_snapshot select 0) isNotEqualTo 1) exitWith {false};
private _rows = _snapshot select 1;
if !(_rows isEqualType [] && {count _rows <= 512}) exitWith {false};
private _json = {
    params ["_value",["_depth",0]];
    if (isNil "_value" || {_depth > 8}) exitWith {false};
    if (_value isEqualType 0) exitWith {finite _value && {abs _value <= 1e12}};
    if (_value isEqualType "") exitWith {count _value <= 4096};
    if (_value isEqualType true) exitWith {true};
    if !(_value isEqualType [] && {count _value <= 256}) exitWith {false};
    private _valid = true;
    {if (isNil "_x" || {!([_x,_depth+1] call _json)}) exitWith {_valid = false;};} forEach _value;
    _valid
};
private _tokens = [];
private _sids = [];
private _rowValid = {
    params ["_row"];
    if (isNil "_row" || {!(_row isEqualType [])} || {count _row != 5}) exitWith {false};
    if !([_row] call _json) exitWith {false};
    _row params ["_kind","_token","_class","_payload","_tie"];
    if !(_kind in ["prepared","syringe"] && {_token isEqualType 0}
        && {_token == floor _token} && {_token > 0} && {_token < 65535}
        && {_class isEqualType ""} && {_payload isEqualType []}
        && {_tie isEqualType []}) exitWith {false};
    if (_token in _tokens || {count _payload != ([3,2] select (_kind == "syringe"))}) exitWith {false};
    private _sid = _payload select 0;
    private _body = _payload select 1;
    if !(_sid isEqualType "" && {_sid != ""} && {count _sid <= 256} && {!(_sid in _sids)}
        && {_body isEqualType []}) exitWith {false};
    if !(isClass (configFile >> "CfgMagazines" >> _class)
        && {getText (configFile >> "CfgMagazines" >> _class >> "ACME_inventoryKind") == _kind}) exitWith {false};
    if (_kind == "syringe") then {
        if (count _body != 14 || {_tie isNotEqualTo []}) exitWith {false};
        if !((_body select 0) isEqualType "" && {(_body select 0) != ""}
            && {(_body select 1) in [1,3,5,10]}
            && {(_body select 2) isEqualType 0} && {(_body select 2) >= 0}
            && {(_body select 4) isEqualType 0} && {(_body select 4) >= 0}
            && {(_body select 2) + (_body select 4) > 0}
            && {(_body select 2) + (_body select 4) <= (_body select 1) + 0.001}
            && {(_body select 5) isEqualType []}
            && {(_body select 11) isEqualTo _sid} && {(_body select 13) == "inventoryB279"}) exitWith {false};
        if (([3,6,7,8,9,10,12] findIf {!((_body select _x) isEqualType "")}) >= 0) exitWith {false};
        private _components = _body select 5;
        if ((_components findIf {!(_x isEqualType [] && {count _x == 2} && {(_x select 0) isEqualType ""}
            && {(_x select 0) != ""} && {(_x select 1) isEqualType 0} && {(_x select 1) > 0})}) >= 0) exitWith {false};
        _tokens pushBack _token; _sids pushBack _sid;
        true
    } else {
        if (count _body < 9 || {count _body > 12} || {(_body select 0) isNotEqualTo _sid}) exitWith {false};
        if (([1,2,3,4,5,6,8] findIf {!((_body select _x) isEqualType "")}) >= 0
            || {(_body select 5) != ""} || {!((_body select 7) isEqualType true)}) exitWith {false};
        if (([9,10] findIf {_x < count _body && {!((_body select _x) isEqualType 0) || {(_body select _x) < 0}}}) >= 0) exitWith {false};
        private _fresh = ((_body select 1) find "ACM_FreshBloodBag_") == 0 || {((_body select 2) find "FreshBloodBag_") == 0};
        if (_fresh && {count _body != 12}) exitWith {false};
        private _meta = _body param [11,[]];
        private _validFresh = {
            params ["_meta"];
            if (_meta isEqualTo ["freshMissingV1"]) exitWith {true};
            _meta isEqualType [] && {count _meta == 4} && {(_meta select 0) == "freshAgeV1"}
                && {(_meta select 1) isEqualType true} && {(_meta select 2) isEqualType 0} && {(_meta select 2) >= 0}
                && {(_meta select 3) isEqualType 0} && {(_meta select 3) in [0,1,2,3,4,5,6,7]}
        };
        if ((_fresh && {!([_meta] call _validFresh)}) || {!_fresh && {_meta isNotEqualTo []}}) exitWith {false};
        if (_tie isNotEqualTo [] && {count _tie != 3 || {!(_tie isEqualTypeAll "")}}) exitWith {false};
        private _med = _payload select 2;
        if !(_med isEqualType []) exitWith {false};
        private _validMed = {
            params ["_med"];
            if (_med isEqualTo []) exitWith {true};
            if (count _med != 17 || {(_med select 0) isNotEqualTo _sid} || {(_med select 15) isNotEqualTo _sid}
                || {(_med select 12) isNotEqualTo ""} || {(_med select 13) isNotEqualTo ""}) exitWith {false};
            if (([1,2,3] findIf {!((_med select _x) isEqualType "")}) >= 0) exitWith {false};
            if (([4,5,6,7,8,9,10,11,16] findIf {!((_med select _x) isEqualType 0) || {(_med select _x) < 0}}) >= 0) exitWith {false};
            private _components = _med select 14;
            if !(_components isEqualType []) exitWith {false};
            if ((_components findIf {!(_x isEqualType [] && {count _x == 3} && {(_x select 0) isEqualType ""}
                && {(_x select 0) != ""} && {(_x select 1) isEqualType 0} && {(_x select 1) >= 0}
                && {(_x select 2) isEqualType 0} && {(_x select 2) >= 0})}) >= 0) exitWith {false};
            true
        };
        if !([_med] call _validMed) exitWith {false};
        _tokens pushBack _token; _sids pushBack _sid;
        true
    }
};
private _valid = true;
{if !([_x] call _rowValid) exitWith {_valid = false;};} forEach _rows;
_valid
