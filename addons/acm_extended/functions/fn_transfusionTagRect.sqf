/* B227: collision-free compact annotations; inputs in the same UI coordinate system. */
params ["_anchor", "_size", "_bounds", "_placed", ["_gap", 0.003], ["_left", false]];
_anchor params ["_ax", "_ay", "_aw", "_ah"];
_size params ["_w", "_h"];
_bounds params ["_bx", "_by", "_bw", "_bh"];
_w = _w min _bw; _h = _h min _bh;
private _x = if (_left) then {_ax - _gap - _w} else {_ax + _aw + _gap};
_x = (_x max _bx) min (_bx + _bw - _w);
private _y = ((_ay + (_ah - _h) / 2) max _by) min (_by + _bh - _h);
private _result = [_x, _y, _w, _h];
private _found = false;
// Nearest free row first, both up and down. Bounded by available canvas rows.
for "_step" from 0 to (ceil (_bh / (_h + _gap))) do {
    {
        private _candidateY = _y + _x * _step * (_h + _gap);
        if (!_found && {_candidateY >= _by} && {_candidateY + _h <= _by + _bh}) then {
            private _r = [_result select 0, _candidateY, _w, _h];
            private _hit = _placed findIf {
                (_r select 0) < (_x select 0) + (_x select 2) + _gap
                && {(_r select 0) + _w + _gap > (_x select 0)}
                && {_candidateY < (_x select 1) + (_x select 3) + _gap}
                && {_candidateY + _h + _gap > (_x select 1)}
            };
            if (_hit < 0) then {_result = _r; _found = true;};
        };
    } forEach [1, -1];
    if (_found) exitWith {};
};
if (_found) then {_result} else {[]}
