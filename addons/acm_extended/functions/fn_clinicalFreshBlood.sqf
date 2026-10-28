/* Copy and normalize native IV bag metadata for medical save/restore.
 * Hung fresh-blood metadata lives at index 10; index 9 remains capacity.
 * Numeric FreshBloodList IDs never cross a restart without inline evidence.
 * Returns a copied HashMap, or [] for malformed native bag collections. */
params ["_bags", ["_mode", "snapshot"]];
if !(_bags isEqualType createHashMap && {_mode in ["snapshot", "restore"]}) exitWith {[]};
private _out = createHashMap;
private _invalid = false;
private _number = {params ["_n"]; _n isEqualType 0 && {finite _n}};
private _metaValid = {
    params ["_meta", "_tag", "_bloodType"];
    _meta isEqualType [] && {count _meta == 4} && {(_meta select 0) isEqualTo _tag}
        && {_bloodType in [0,1,2,3,4,5,6,7]}
        && {(_meta select 1) isEqualType true}
        && {[_meta select 2] call _number} && {[_meta select 3] call _number}
        && {(_meta select 3) isEqualTo _bloodType}
};
private _registry = missionNamespace getVariable ["ACM_circulation_FreshBloodList", createHashMap];
{
    private _part = _x;
    private _rows = _bags get _part;
    if !(_part isEqualType "" && {_rows isEqualType []}) exitWith {_invalid = true;};
    private _copied = [];
    {
        if !(_x isEqualType [] && {count _x >= 7} && {(_x select 0) isEqualType ""}
            && {(_x select 4) isEqualType true}
            && {private _row = _x; ([1,2,3,5,6] findIf {!([_row select _x] call _number)}) < 0}
            && {count _x < 8 || {[_x select 7] call _number}}
            && {count _x < 9 || {(_x select 8) isEqualType ""}}
            && {count _x < 10 || {[_x select 9] call _number}}) exitWith {_invalid = true;};
        private _bag = +_x;
        if ((_bag select 0) == "FreshBlood") then {
            private _meta = _bag param [10, []];
            private _next = ["freshMissingV1"];
            private _bloodType = _bag select 5;
            if (_mode == "snapshot") then {
                // A live, un-fenced legacy bag may still have a current donor
                // registry entry. Capture immutable provenance before restart.
                if (_meta isEqualTo [] && {_registry isEqualType createHashMap}) then {
                    private _fresh = _registry getOrDefault [_bag param [7, -1], []];
                    if (_fresh isEqualType [] && {count _fresh >= 5}
                        && {(_fresh select 3) isEqualType true}
                        && {[_fresh select 2] call _number} && {(_fresh select 2) isEqualTo _bloodType}
                        && {[_fresh select 4] call _number}) then {
                        _meta = ["freshV1", _fresh select 3, _fresh select 4, _fresh select 2];
                    };
                };
                if ([_meta, "freshV1", _bloodType] call _metaValid) then {
                    _next = ["freshAgeV1", _meta select 1, (CBA_missionTime - (_meta select 2)) max 0, _bloodType];
                };
            } else {
                if ([_meta, "freshAgeV1", _bloodType] call _metaValid && {(_meta select 2) >= 0}) then {
                    _next = ["freshV1", _meta select 1, CBA_missionTime - (_meta select 2), _bloodType];
                };
            };
            if (count _bag < 8) then {_bag set [7, -1];};
            if (count _bag < 9) then {_bag set [8, ""];};
            if (count _bag < 10) then {_bag set [9, _bag select 6];};
            _bag set [10, _next];
            if (_mode == "restore") then {_bag set [7, -1];};
        };
        _copied pushBack _bag;
    } forEach _rows;
    if (_invalid) exitWith {};
    _out set [_part, _copied];
} forEach keys _bags;
if (_invalid) exitWith {[]};
_out
