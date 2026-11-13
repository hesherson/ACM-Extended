/* Sustain the next reserved R wave across packets, including fractional and irregular RR. */
params ["_at","_until","_rr","_rhythm","_clock"];
_clock params [["_beat",_at],["_prior",_rr],["_next",_rr],["_serial",0]];
if (_at - _beat > 8 || {_at < _beat-0.1}) then {_beat = _at;_prior = _rr;_next = _rr;};
private _irregular = _rhythm in [100,103];
private _advance = {
    _beat = _beat + _next;
    _serial = _serial + 1;
    _prior = _next;
    _next = if (_irregular) then {_rr * (0.75+0.5*((sin (_serial*137)+1)/2))} else {_rr};
};
while {_beat+_next <= _at} do {call _advance;};
private _beats = [[_beat-_prior,_serial-1],[_beat,_serial]];
private _carry = [_beat,_prior,_next,_serial];
while {_beat < _until} do {
    _carry = [_beat,_prior,_next,_serial];
    call _advance;
    _beats pushBack [_beat,_serial];
};
[_carry,_beats]
