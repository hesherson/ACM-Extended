/* Column-major alphabetical medication pairs. Does not mutate the cached catalog or source rows. */
params [["_rows", [], [[]]]];
private _labels = [];
private _byLabel = createHashMap;
{
    private _label = toLowerANSI (_x param [0, ""]);
    if !(_label in _byLabel) then {_labels pushBack _label; _byLabel set [_label, []];};
    (_byLabel get _label) pushBack (+_x);
} forEach _rows;
_labels sort true;
private _ordered = [];
{_ordered append (_byLabel get _x);} forEach _labels;
private _height = ceil ((count _ordered) / 2);
private _pairs = [];
for "_row" from 0 to (_height - 1) do {
    private _pair = +(_ordered select _row);
    private _right = _row + _height;
    if (_right < count _ordered) then {_pair append (_ordered select _right);};
    _pairs pushBack _pair;
};
_pairs
