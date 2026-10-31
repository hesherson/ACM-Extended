/* Read-only relation between visible native rows and one exact Y access.
 * lbValue owns the selection index; row order and fluid names alone cannot link bags.
 * Ambiguous duplicate branches or intervening unrelated rows keep their native Y tags.
 */
params ["_selection", "_rowValues", "_part", "_iv", "_site", "_yLines"];
if (_part == "" || {_site < 0}) exitWith {[[], ""]};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
if !(_key in (_yLines apply {toLowerANSI _x})) exitWith {[[], ""]};
private _blood = []; private _saline = [];
{
    private _value = _x;
    if (_value >= 0 && {_value < count _selection}) then {
        private _bag = _selection select _value;
        if ((_bag param [3, -1]) == _site && {(_bag param [4, false]) isEqualTo _iv}) then {
            private _type = _bag param [0, ""];
            if (_type in ["Blood", "FreshBlood", "ACME_Empty"]) then {_blood pushBack _forEachIndex;};
            if (_type in ["Saline", "ACME_SalineY", "ACME_EmptySaline"]) then {_saline pushBack _forEachIndex;};
        };
    };
} forEach _rowValues;
if (count _blood > 1 || {count _saline > 1}) exitWith {[[], _key]};
private _rows = _blood + _saline;
_rows sort true;
if (count _rows == 2 && {(_rows select 1) - (_rows select 0) != 1}) then {_rows = [];};
[_rows, _key]
