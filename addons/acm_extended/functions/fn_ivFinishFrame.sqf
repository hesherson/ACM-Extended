/* Original assets run at 30 fps, without looping. The no-return branch reverses
   its FULL syringe connection frames to unlock and remove it without injection. */
params ["_sequence", "_elapsed"];
private _rate = if (_sequence in ["blood_return_flush","resisted_no_return"]) then {1.25} else {1};
private _frame = floor ((_elapsed max 0) * 30 * _rate);
switch (_sequence) do {
    case "blood_return_flush": {
        if (_frame >= 180) then {_sequence = "post_flush_secure"; _frame = (_frame - 180) min 41;};
    };
    case "resisted_no_return": {
        if (_frame >= 120) then {_frame = (47 - (_frame - 120)) max 0;};
    };
    case "extension_attach": {_frame = _frame min 23;};
    case "iv_line_attach": {_frame = _frame min 29;};
    case "tegaderm_apply": {_frame = _frame min 35;};
    default {_sequence = "extension_attach"; _frame = 0;};
};
private _digits = str _frame;
while {count _digits < 4} do {_digits = "0" + _digits;};
format ["\acm_extended\ui\iv\finish\%1_%2_ca.paa",_sequence,_digits]
