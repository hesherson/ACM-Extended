#include "..\script_component.hpp"
/*
 * ACME 1.3.0 blast ocular injury.
 *
 * CBA's per-unit "explosion" class event supplies [unit, damage]. The imported implementation
 * expected a source object that this event does not guarantee and therefore could not be made
 * owner-authoritative for remote casualties. Use the engine's already proximity-scaled damage as
 * the blast-strength input instead.
 */
params ["_unit", ["_damage",0,[0]]];

if (!GVAR(enable) || {isNull _unit} || {!local _unit} || {!alive _unit} || {_damage <= 0}) exitWith {};

private _strength = linearConversion [0.05,0.80,_damage,0,1,true];
if (_strength <= 0.10) exitWith {};

private _eyeProtection = [_unit] call FUNC(getEyeProtection);
private _unprotected = 1 - (_eyeProtection max 0 min 1);

// Blink is presentation only. Durable injury state is still created for AI and other players.
if (hasInterface && {_unit isEqualTo ACE_player}) then {
    [0.15 + (0.40 * _strength),true] call FUNC(effectEyeBlink);
};

private _heavyPercent = GVAR(probability_dust_heavy)
    * linearConversion [0.10,1,_strength,0.35,2.5,true]
    * _unprotected;

if ((random 100) < _heavyPercent) then {
    private _eyes = _unit getVariable [QGVAR(eyeInjuries),[1,1]];
    if !(_eyes isEqualType [] && {count _eyes == 2}) then {_eyes = [1,1];};

    // A blast can injure one or both eyes. Bilateral structural injury is reserved for the
    // strongest unprotected exposures; ordinary events damage one random eye.
    private _first = floor random 2;
    _eyes set [_first,0];
    if (_strength > 0.85 && {_unprotected > 0.75} && {random 1 < 0.25}) then {
        _eyes set [1 - _first,0];
    };

    _unit setVariable [QGVAR(eyeInjuries),_eyes,true];
    _unit setVariable [QGVAR(eyeInjurySevere),({ _x < 0.25 } count _eyes) >= 2,true];
    _unit setVariable [QGVAR(structuralLastTick),CBA_missionTime,false];

    if (hasInterface && {_unit isEqualTo ACE_player}) then {
        [true,_eyes] call FUNC(effectHurtEye);
    };
} else {
    // Non-structural blast irritation remains eyewash-reversible.
    private _dust = _unit getVariable [QGVAR(dustInjuryLight),0];
    private _increase = (0.35 + (0.9 * _strength)) * (1 - (_eyeProtection * 0.75));
    if (_increase > 0.05) then {
        _unit setVariable [QGVAR(dustInjuryLight),(_dust + _increase) min 5,true];
        if (hasInterface && {_unit isEqualTo ACE_player}) then {
            [true,GET_DUST_INJURY(_unit)] call FUNC(effectEyeInjury);
        };
    };
};
