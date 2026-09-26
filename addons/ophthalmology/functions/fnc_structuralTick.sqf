#include "..\script_component.hpp"
/*
 * ACME 1.3.0 owner-local structural ocular-trauma tick.
 * Irritant/dust injury remains a separate eyewash-reversible state.
 * No per-patient PFH is created; XEH_postInit owns one locality-safe global worker.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
if !(_eyes isEqualType [] && {count _eyes == 2}) exitWith {};
private _injured = ({_x < 0.999} count _eyes) > 0;
private _shieldItem = _patient getVariable [QGVAR(eyeShieldItem),""];
private _shieldIndex = (_patient getVariable [QGVAR(eyeShieldIndex),-1]) max -1 min 1;
private _shieldActive = _shieldItem != "" && {(hmd _patient) == _shieldItem} && {_shieldIndex >= 0};

if (!_injured) exitWith {
    _patient setVariable [QGVAR(eyeInjurySevere),false,true];
    _patient setVariable [QGVAR(ocularPermanent),false,true];
    if (!_shieldActive) then {
        _patient setVariable [QGVAR(eyeShieldItem),"",true];
        _patient setVariable [QGVAR(eyeShieldIndex),-1,true];
    };
    if (hasInterface && {_patient isEqualTo ACE_player} && {!_shieldActive}) then {
        [] call FUNC(hideEyeShieldOverlay);
    };
};

private _now = CBA_missionTime;
private _last = _patient getVariable [QGVAR(structuralLastTick),_now - 1];
private _dt = ((_now - _last) max 0) min 5;
_patient setVariable [QGVAR(structuralLastTick),_now,false];

private _hardcore = missionNamespace getVariable ["ACME_hcEff_ophthalmology",false];
if (_hardcore) then {
    // Structural ocular trauma is stabilized, not field-cured. This setting is explicitly the
    // evacuation variant, so latch only TRUE here and let full-heal/definitive-care reset it.
    if !(_patient getVariable [QGVAR(ocularPermanent),false]) then {
        _patient setVariable [QGVAR(ocularPermanent),true,true];
        if (!isNil "ACME_fnc_evacuationRequirementCommit") then {
            [_patient,true,true,true,false] call ACME_fnc_evacuationRequirementCommit;
        } else {
            _patient setVariable ["ACME_requiresEvac",true,true];
        };
    };
} else {
    // Arma normal mode cannot turn a single eye injury into an unavoidable mission-long burden.
    // Protection meaningfully accelerates recovery, while unprotected structural injury resolves
    // at half speed. This is deliberately game-compressed and not a claim of real ocular healing time.
    private _minutes = GVAR(structuralRecoveryMinutes) max 1;
    private _rate = 1 / (_minutes * 60);
    if (!_shieldActive) then {_rate = _rate * 0.5;};

    for "_i" from 0 to 1 do {
        private _v = (_eyes select _i) max 0 min 1;
        if (_v < 1) then {
            // A shield preferentially protects/treats the covered eye; the other eye can still
            // recover slowly in ordinary gameplay.
            private _mult = if (_shieldActive && {_i == _shieldIndex}) then {1} else {0.5};
            _eyes set [_i, (_v + (_rate * _mult * _dt)) min 1];
        };
    };
    _patient setVariable [QGVAR(eyeInjuries),_eyes,true];
    _patient setVariable [QGVAR(ocularPermanent),false,true];
};

private _severe = ({_x < 0.25} count _eyes) >= 2;
_patient setVariable [QGVAR(eyeInjurySevere),_severe,true];

// Shield overlay is presentation-only and follows the affected local player.
if (hasInterface && {_patient isEqualTo ACE_player}) then {
    if (_shieldActive) then {
        private _displayId = [17103,17102] select _shieldIndex;
        [_displayId] call FUNC(showEyeShieldOverlay);
    } else {
        [] call FUNC(hideEyeShieldOverlay);
    };
};
