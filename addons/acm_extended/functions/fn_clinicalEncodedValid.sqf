/* NA4 structural preflight for the tagged v3 codec. No input is compiled.
   A shared node budget bounds recursion before a restore can clear the patient. */
params ["_v", ["_depth", 0], ["_budget", [100000]]];
if (isNil "_v") exitWith {false};
if (_depth > 24 || {(_budget select 0) <= 0}) exitWith {false};
_budget set [0, (_budget select 0) - 1];
if !(_v isEqualType [] && {count _v > 0} && {!isNil {_v select 0}} && {(_v select 0) isEqualType ""}) exitWith {false};
private _n = count _v;
switch (_v select 0) do {
    case "N": {_n == 1};
    case "V": {
        _n == 2 && {!isNil {_v select 1}} && {private _x = _v select 1;
            _x isEqualType true || {_x isEqualType ""} || {_x isEqualType 0 && {finite _x}}
        }
    };
    case "O": {
        _n in [2,4] && {!isNil {_v select 1}} && {(_v select 1) isEqualType ""} && {count (_v select 1) <= 128}
            && {_n == 2 || {
                !isNil {_v select 2} && {!isNil {_v select 3}}
                    && {(_v select 2) isEqualType ""} && {count (_v select 2) <= 256}
                    && {(_v select 3) isEqualType ""} && {count (_v select 3) <= 256}
            }}
    };
    case "T": {_n == 3 && {!isNil {_v select 1}} && {!isNil {_v select 2}} && {(_v select 1) in ["time","cba"]} && {(_v select 2) isEqualType 0} && {finite (_v select 2)}};
    case "A": {
        _n == 2 && {!isNil {_v select 1}} && {(_v select 1) isEqualType []} && {
            ((_v select 1) findIf {!([_x, _depth + 1, _budget] call ACME_fnc_clinicalEncodedValid)}) < 0
        }
    };
    case "M": {
        if !(_n == 2 && {!isNil {_v select 1}} && {(_v select 1) isEqualType []}) exitWith {false};
        private _seen = createHashMap;
        ((_v select 1) findIf {
            if !(_x isEqualType [] && {count _x == 2}) exitWith {true};
            if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {true};
            private _key = _x select 0;
            if !(typeName _key in ["STRING","SCALAR","BOOL"]) exitWith {true};
            if (_key isEqualType 0 && {!finite _key}) exitWith {true};
            if (_key in _seen) exitWith {true};
            _seen set [_key, true];
            !([_x select 1, _depth + 1, _budget] call ACME_fnc_clinicalEncodedValid)
        }) < 0
    };
    default {false};
}
