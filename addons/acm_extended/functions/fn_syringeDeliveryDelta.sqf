/* Pure, all-or-nothing syringe arithmetic for the server delivery journal.
 * Never mutate a caller's row/components. A missing or malformed quantity is
 * unresolved evidence, not a zero-volume default. Metadata remains unchanged.
 */
if (isNil "_this") exitWith {[]};
if !(_this isEqualType [] && {count _this in [2,3]}) exitWith {[]};
private _row = _this select 0;
private _delta = _this select 1;
private _restore = false;
if (count _this == 3) then {_restore = _this select 2;};
if (isNil "_row" || {isNil "_delta"} || {isNil "_restore"}) exitWith {[]};
if !(_row isEqualType [] && {count _row >= 6}
    && {_delta isEqualType []} && {count _delta == 3}
    && {_restore isEqualType false}) exitWith {[]};
private _size = _row select 1;
private _currentDrug = _row select 2;
private _currentNs = _row select 4;
private _parts = _row select 5;
private _drug = _delta select 0;
private _ns = _delta select 1;
private _changes = _delta select 2;
if (isNil "_size" || {isNil "_currentDrug"} || {isNil "_currentNs"}
    || {isNil "_parts"} || {isNil "_drug"} || {isNil "_ns"} || {isNil "_changes"}) exitWith {[]};
if !(_size isEqualType 0 && {finite _size} && {_size in [1,3,5,10]}
    && {_currentDrug isEqualType 0} && {finite _currentDrug} && {_currentDrug >= 0}
    && {_currentNs isEqualType 0} && {finite _currentNs} && {_currentNs >= 0}
    && {_currentDrug + _currentNs <= _size + 0.001}
    && {_parts isEqualType []}
    && {_drug isEqualType 0} && {finite _drug} && {_drug >= 0}
    && {_ns isEqualType 0} && {finite _ns} && {_ns >= 0}
    && {_changes isEqualType []}) exitWith {[]};

private _valid = true;
private _componentTotal = 0;
private _newParts = [];
{
    if (isNil "_x") then {_valid = false; continue;};
    if !(_x isEqualType [] && {count _x == 2}) then {_valid = false; continue;};
    private _source = _x select 0;
    private _ml = _x select 1;
    if (isNil "_source" || {isNil "_ml"}) then {_valid = false; continue;};
    if !(_source isEqualType "" && {_source != ""}
        && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0}) then {
        _valid = false;
    } else {
        _componentTotal = _componentTotal + _ml;
        _newParts pushBack +_x;
    };
} forEach _parts;
if (!_valid || {!finite _componentTotal}
    || {count _parts > 0 && {abs (_componentTotal - _currentDrug) > 0.001}}) exitWith {[]};

private _seen = [];
private _deltaTotal = 0;
{
    if (isNil "_x") then {_valid = false; continue;};
    if !(_x isEqualType [] && {count _x == 3}) then {_valid = false; continue;};
    private _index = _x select 0;
    private _source = _x select 1;
    private _ml = _x select 2;
    if (isNil "_index" || {isNil "_source"} || {isNil "_ml"}) then {_valid = false; continue;};
    if !(_index isEqualType 0 && {finite _index} && {_index == floor _index}
        && {_index >= 0} && {_index < count _parts} && {!(_index in _seen)}
        && {_source isEqualType ""} && {_source != ""}
        && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0}) then {
        _valid = false;
        continue;
    };
    private _part = +(_newParts select _index);
    private _current = _part select 1;
    if ((_part select 0) != _source || {!_restore && {_ml > _current + 0.000001}}) then {
        _valid = false;
        continue;
    };
    _seen pushBack _index;
    _deltaTotal = _deltaTotal + _ml;
    _part set [1,if (_restore) then {_current + _ml} else {(_current - _ml) max 0}];
    _newParts set [_index,_part];
} forEach _changes;
if (!_valid || {!finite _deltaTotal}
    || {count _parts > 0 && {abs (_deltaTotal - _drug) > 0.001}}
    || {!_restore && {_drug > _currentDrug + 0.000001 || {_ns > _currentNs + 0.000001}}}) exitWith {[]};
private _newDrug = if (_restore) then {_currentDrug + _drug} else {(_currentDrug - _drug) max 0};
private _newNs = if (_restore) then {_currentNs + _ns} else {(_currentNs - _ns) max 0};
if (!finite _newDrug || {!finite _newNs} || {_newDrug + _newNs > _size + 0.001}) exitWith {[]};
private _newTotal = 0;
{
    private _ml = _x select 1;
    if (!finite _ml) then {_valid = false;};
    _newTotal = _newTotal + _ml;
} forEach _newParts;
if (!_valid || {!finite _newTotal}
    || {count _newParts > 0 && {abs (_newTotal - _newDrug) > 0.001}}) exitWith {[]};
private _out = +_row;
_out set [2,_newDrug];
_out set [4,_newNs];
_out set [5,_newParts];
_out
