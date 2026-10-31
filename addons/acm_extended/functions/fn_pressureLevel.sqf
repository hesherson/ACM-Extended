/* B304: pressure follows actual volume remaining in this physical bag, never elapsed time.
 * The fourth cuff field anchors pressure to the remaining mL at the last pump.
 * Legacy cuffs retain their stored pressure until owner maintenance anchors them. */
params [["_cuff", [], [[]]], ["_remaining", -1, [0]]];
if (_cuff isEqualTo []) exitWith {0};
private _p = ((_cuff param [1,0]) max 0) min 1;
private _anchor = _cuff param [3,0];
if (_anchor > 0 && {_remaining >= 0}) then {
    _p = _p * (((_remaining / _anchor) max 0) min 1);
};
_p
