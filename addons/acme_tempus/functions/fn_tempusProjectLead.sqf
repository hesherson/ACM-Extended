/* Project the shared LifePak beat into limb and precordial leads.
 * P, QRS and T have separate axes. All leads preserve the electrical event time.
 */
params ["_lead","_samples","_phases"];
if (_lead == "II") exitWith {_samples apply {round (_x*10)/10}};
private _profile = switch (_lead) do {
    case "I":   {[0.5,0.35,0.65,0.80]};
    case "V1":  {[-0.12,-0.1,0.36,1.05]};
    case "V2":  {[0.22,-0.18,0.46,1.16]};
    case "V3":  {[0.44,0.28,0.76,1.05]};
    case "V4":  {[0.71,0.78,1.13,0.90]};
    case "V5":  {[0.74,0.93,1.06,0.56]};
    case "V6":  {[0.66,0.84,0.86,0.39]};
    default     {[0.5,0.35,0.65,0.80]}; // Reconstruct the other five limb leads from I and II.
};
_profile params ["_p","_t","_r","_s"];
private _trace = [];
{
    private _ii = _x;
    private _phase = _phases param [_forEachIndex,99];
    private _gain = if (_phase < -2) then {_p} else {
        if (_phase > 3) then {_t} else {[_r,_s] select (_phase >= 1 && {_ii > 0})}
    };
    if (_phase == 99) then {_gain = (_r+_s)*0.5;};
    private _projection = _ii * _gain;
    private _result = switch (_lead) do {
        case "III": {_ii-_projection};
        case "AVR": {-(_projection+_ii)/2};
        case "AVL": {_projection-_ii/2};
        case "AVF": {_ii-_projection/2};
        default {_projection};
    };
    _trace pushBack (round (_result*10)/10);
} forEach _samples;
_trace
