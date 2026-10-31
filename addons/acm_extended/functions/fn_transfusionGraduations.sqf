/* Native bag scale: [fraction, mL] marks, bounded to eleven controls per card. */
params [["_volume",0,[0]]];
if (!finite _volume || {_volume <= 0}) exitWith {[]};
private _step = switch (round _volume) do {
    case 50: {10}; case 100: {20}; case 250: {50}; case 500: {100}; case 1000: {100};
    default {private _steps = [5,10,20,25,50,100,200,250,500,1000,2000]; _steps param [_steps findIf {_volume / _x <= 10},2000]};
};
private _marks = [];
for "_mark" from 0 to ((floor (_volume / _step)) min 10) do {
    private _ml = _mark * _step;
    _marks pushBack [_ml / _volume, _ml];
};
_marks
