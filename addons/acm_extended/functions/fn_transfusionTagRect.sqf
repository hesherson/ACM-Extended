/* B275: outward fluid callout with a diagonal into its top inner corner. */
params ["_anchor", "_size", "_bounds", "_placed", ["_gap", 0.003], ["_left", false], ["_above", true]];
_anchor params ["_ax", "_ay", "_aw", "_ah"];
_size params ["_w", "_h"];
_bounds params ["_bx", "_by", "_bw", "_bh"];
if (_bw <= 0 || {_bh <= 0} || {_w <= 0} || {_h <= 0}) exitWith {[]};
_w = _w min _bw;
_h = _h min _bh;
private _leaderW = (_gap * 3) max (_aw * 0.35);
private _labelX = if (_left) then {_ax - _leaderW - _w} else {_ax + _aw + _leaderW};
_labelX = (_labelX max _bx) min (_bx + _bw - _w);
private _anchorY = _ay + _ah / 2;
private _preferredY = if (_above) then {_ay - _gap - _h} else {_ay + _ah + _gap};
_preferredY = (_preferredY max _by) min (_by + _bh - _h);
private _result = [];
private _rowH = _h + _gap;
private _directions = if (_above) then {[-1,1]} else {[1,-1]};
// Existing labels stay fixed while the nearest free outward row is found.
for "_step" from 0 to (ceil (_bh / _rowH)) do {
    {
        private _candidateY = _preferredY + _x * _step * _rowH;
        if (_result isEqualTo [] && {_candidateY >= _by} && {_candidateY + _h <= _by + _bh}
            && {abs (_candidateY - _anchorY) >= _gap}) then {
            private _r = [_labelX, _candidateY, _w, _h];
            private _hit = _placed findIf {
                (_r select 0) < (_x select 0) + (_x select 2) + _gap
                && {(_r select 0) + _w + _gap > (_x select 0)}
                && {_candidateY < (_x select 1) + (_x select 3) + _gap}
                && {_candidateY + _h + _gap > (_x select 1)}
            };
            if (_hit < 0) then {_result = _r;};
        };
    } forEach _directions;
    if (_result isNotEqualTo []) exitWith {};
};
_result
