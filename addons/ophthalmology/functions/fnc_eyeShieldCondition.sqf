#include "..\script_component.hpp"
/*
 * Eye shield is for structural ocular trauma. One shield can occupy the HMD slot at a time.
 */
params ["_medic", "_patient"];

private _eyeInjuries = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
private _needs = ({_x < 0.999} count _eyeInjuries) > 0;
private _shield = hmd _patient;
_needs && {!(_shield in ["kat_eyecovers_left","kat_eyecovers_right","kat_eyecovers"])}
