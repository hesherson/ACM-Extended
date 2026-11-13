/* All dose consumers use the same class profile and server-selected scale.
 * modes: physical (remaining amount), effect (with native onset), active (record lifetime). */
params ["_record","_age",["_mode","effect"]];
_record params ["_class","","_onset","_nativeDuration","","","","_route","_plateau"];
private _profile = [_class] call ACME_fnc_medicationHalfLife;
private _scale = (missionNamespace getVariable ["ACME_clinicalTiming",[]]) param [0,1];
private _half = 0;
if (_profile isNotEqualTo []) then {_half = _profile param [1,(_profile select 0)];};
private _physical = {
    if (_profile isEqualTo []) exitWith {linearConversion [_onset+_plateau,_nativeDuration,_age,1,0,true]};
    [_age,_onset,_route,_profile,_scale] call ACME_fnc_medicationResidual
};
if (_mode == "physical") exitWith {call _physical};
if (_mode == "active") exitWith {
    if (_age < _nativeDuration) exitWith {true};
    if (_half > 0 && {_age < (_onset+_plateau+10*_half*_scale)}) exitWith {true};
    (call _physical) > 0
};
[_route,_age,_onset,_nativeDuration,_plateau,0,_half*_scale] call ACM_circulation_fnc_getMedicationEffect
