/* Available amount, in fractions of the delivered dose. Use age from dose admission,
 * allowing depot absorption time for non-IV routes. Discard less than 0.1% of a dose. */
params ["_age","_onset","_route","_profile","_scale"];
_profile params ["_half",["_clinical",0],["_initial",0],["_share",0]];
private _elapsed = (_age - ([0,_onset] select (_route != 1))) max 0;
private _fraction = (1-_share) * (0.5 ^ (_elapsed / (_half*_scale)));
if (_share > 0) then {_fraction = _fraction + _share * (0.5 ^ (_elapsed / (_initial*_scale)));};
if (_fraction < 0.001) exitWith {0};
_fraction
