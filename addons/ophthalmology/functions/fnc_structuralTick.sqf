#include "..\script_component.hpp"
/*
 * ACME 1.3.0 owner-local structural ocular-trauma tick.
 * Irritant/dust injury remains a separate eyewash-reversible state.
 * No per-patient PFH is created; XEH_postInit owns one locality-safe global worker.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
if !(_eyes isEqualType [] && {count _eyes == 2}
    && {(_eyes findIf {!(_x isEqualType 0) || {!finite _x}}) == -1}) exitWith {};
private _injured = ({_x < 0.999} count _eyes) > 0;
private _shieldItem = _patient getVariable [QGVAR(eyeShieldItem),""];
private _shieldIndex = _patient getVariable [QGVAR(eyeShieldIndex),-1];
private _shieldActive = _shieldIndex in [0,1]
    && {_shieldItem == (["kat_eyecovers_right","kat_eyecovers_left"] select _shieldIndex)}
    && {(hmd _patient) == _shieldItem};
private _permanent = _patient getVariable [QGVAR(ocularPermanent),false];

if (!_injured && {!_permanent}) exitWith {
    // The worker's tolerance must not strand a tiny residual injury/GUI label forever.
    if !(_eyes isEqualTo [1,1]) then {_patient setVariable [QGVAR(eyeInjuries),[1,1],true];};
    _patient setVariable [QGVAR(eyeInjurySevere),false,true];
    if (!_shieldActive) then {
        _patient setVariable [QGVAR(eyeShieldItem),"",true];
        _patient setVariable [QGVAR(eyeShieldIndex),-1,true];
    };
};

private _now = CBA_missionTime;
private _last = _patient getVariable [QGVAR(structuralLastTick),_now - 1];
private _dt = ((_now - _last) max 0) min 5;
_patient setVariable [QGVAR(structuralLastTick),_now,false];

private _hardcore = missionNamespace getVariable ["ACME_hcEff_ophthalmology",false];

if (_hardcore && {!_permanent}) then {
    // Hardcore causes the permanent field limitation. Once latched, changing a mission setting
    // does not retroactively heal an eye; definitive reset/evacuation is the release boundary.
    _permanent = true;
    _patient setVariable [QGVAR(ocularPermanent),true,true];
};

if (_permanent) then {
    if !(_patient getVariable ["ACME_requiresEvac",false]) then {
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

    for "_i" from 0 to 1 do {
        private _v = (_eyes select _i) max 0 min 1;
        if (_v < 1) then {
            // A shield preferentially protects/treats the covered eye; the other eye can still
            // recover slowly in ordinary gameplay.
            private _mult = if (_shieldActive && {_i == _shieldIndex}) then {1} else {0.5};
            private _next = (_v + (_rate * _mult * _dt)) min 1;
            if (_next >= 0.999) then {_next = 1;};
            _eyes set [_i,_next];
        };
    };
    _patient setVariable [QGVAR(eyeInjuries),_eyes,true];
};

private _severe = ({_x < 0.25} count _eyes) >= 2;
_patient setVariable [QGVAR(eyeInjurySevere),_severe,true];

// updateVisualEffects is the single presentation worker. It follows controlled-unit,
// consciousness and HMD changes without the slower physiology worker reopening an old overlay.
