/*
 * Where a rescuer is local: his walking speed while he drags or carries. Two things ask for a share of it, the
 * rubber band between two litter bearers (fn_carryBand.sqf: acme_carry_coef) and the jog (fn_dragPace.sqf:
 * acme_pace_jog), and since B395 the pull of a medical line near the end of its reach (acm_extended
 * fn_lineTension.sqf: acme_line_coef); this sets the speed of his animations to their product. While either is at work ACE's fatigue
 * is told to leave that speed alone (it sets it itself once a second); when neither is, he has his own speed
 * back.
 * Arguments: 0: rescuer.
 */
params ["_unit"];
private _ours = (_unit getVariable ["acme_carry_banded", false]) || {_unit getVariable ["acme_drag_jogging", false]}
    || {(_unit getVariable ["acme_line_coef", 1]) < 0.999};
if (!_ours) exitWith {
    if (_unit getVariable ["acme_pace_on", false]) then {
        _unit setVariable ["acme_pace_on", nil];
        if (!isNil "ace_advanced_fatigue_setAnimExclusions") then {
            ace_advanced_fatigue_setAnimExclusions = ace_advanced_fatigue_setAnimExclusions - ["acme_pace"];
        };
        _unit setAnimSpeedCoef 1;
    };
};
if !(_unit getVariable ["acme_pace_on", false]) then {
    _unit setVariable ["acme_pace_on", true];
    if (!isNil "ace_advanced_fatigue_setAnimExclusions") then {ace_advanced_fatigue_setAnimExclusions pushBackUnique "acme_pace";};
};
_unit setAnimSpeedCoef ((_unit getVariable ["acme_carry_coef", 1]) * (_unit getVariable ["acme_pace_jog", 1]) * (_unit getVariable ["acme_line_coef", 1]));
