/* Deterministic game model: no patient, random, clock, UI or network reads.
Context: [openHoles,totalHoles,outflow,bleedSource,ppvFactor,hasDrain,sealOutlet,definitiveDrain].
Air/leak are normalized simulation quantities, not clinical volumes/rates. */
params ["_state","_context","_dt",["_tension",false],["_baseSec",600],["_healSec",600],["_stableSec",60]];
_state=+_state;
_dt=_dt max 0 min 5;
if (_dt<=0) exitWith {[_state,_tension]};
_context params ["_open","_holes","_out","_blood","_ppv","_drain","_seal"];
// The optional final field preserves older seven-field calibration callers.
private _definitiveDrain = _context param [7, false, [false]];
private _qualifiedObservation = count _context >= 8;
_state params ["_version","_air","_leak","_stable","_pressure","_ncd","_serial","_last","_residual"];
_baseSec=_baseSec max 60;
_healSec=_healSec max 60;
_stableSec=_stableSec max 0 min 86400;
_out=_out max 0;
_ppv=_ppv max 1 min 3;
// Minor internal leaks can close. External openings still admit air until
// covered. Unconsciousness, sedation and unrelated shock do not drive PTX.
private _endLeak=(_leak-(_dt/(_healSec*(1+0.5*(_blood max 0 min 1))))) max 0;
private _meanLeak=(_leak+_endLeak)*0.5;
private _in=_meanLeak*_ppv+((0.35*(_open max 0)) min 1.4);
private _net=_in-_out;
private _oldAir=_air;
if (_net>0) then {
    _air=(_air+4*_net*_dt/_baseSec) min 32;
    if (_air>2) then {_pressure=(_pressure+_net*(_air-1)*_dt/_baseSec) min 1;};
    _stable=0;
} else {
    // Actual drainage removes accumulated gas, preserving residual collapse.
    _air=(_air+4*_net*_dt/60) max _residual;
    if (!_tension) then {_pressure=(_pressure-_dt/60) max 0;} else {
        if (_net < -0.000001) then {
            _pressure=(_pressure-(-_net)*_dt/15) max 0;
            if (_pressure<=0.1 && {_air<3}) then {_tension=false;};
        };
    };
    if (!_tension && {_air<=_oldAir+0.000001}) then {_stable=(_stable+_dt) min _stableSec;} else {_stable=0;};
};
if (_pressure>=1 && {_net>0}) then {_tension=true;_stable=0;};
// B271 gameplay stability: definitive drainage can settle this injury's internal
// leak after a full, controlled observation interval. Procedure entry and every
// new injury reset the observation clock. NCD and ordinary wound seals retain
// natural healing; their quiet timers cannot earn this definitive-drain benefit.
if (_qualifiedObservation) then {
    private _controlled = !_tension && {_open == 0} && {_air <= 1}
        && {_pressure <= 0.1} && {_air <= _oldAir + 0.000001} && {_net <= 0};
    if (!_controlled) then {
        _stable = 0;
    } else {
        if (_definitiveDrain && {_stable >= _stableSec}) then {_endLeak = 0;};
    };
};
// A stopped leak cannot generate pressure. Established tension still requires
// venting; a quiet timer alone must not silently treat tension physiology.
_state set [1,_air max 0 min 32];
_state set [2,_endLeak];
_state set [3,_stable];
_state set [4,_pressure max 0 min 1];
[_state,_tension]
