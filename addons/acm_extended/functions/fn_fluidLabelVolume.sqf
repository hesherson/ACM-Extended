/* Replace the volume token only. Keep donor type/ID, localization, item name and attached tags intact.
 * mL/ml, spaces and compact native labels are accepted. FBTK uses its filled volume rather than capacity. */
params [["_label", "", [""]], ["_remaining", 0, [0]]];
private _amount = str (round (_remaining max 0));
private _at = (toLowerANSI _label) find "ml";
if (_at < 0) exitWith {_label + format [" (%1 mL)", _amount]};
private _end = _at;
while {_end > 0 && {(_label select [_end - 1, 1]) in [" ", toString [160]]}} do {_end = _end - 1;};
private _start = _end;
while {_start > 0 && {(_label select [_start - 1, 1]) in ["0","1","2","3","4","5","6","7","8","9",".",","]}} do {_start = _start - 1;};
if (_start == _end) exitWith {_label + format [" (%1 mL)", _amount]};
(_label select [0, _start]) + _amount + (_label select [_end])
