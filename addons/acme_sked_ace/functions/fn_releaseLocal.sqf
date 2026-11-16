/*
 * Where the casualty is local: detach them from the SKED, put them in the ACE pose for their state, and
 * give back the unsqueezed HPMK-I shell (dead or alive).
 * Arguments: 0: casualty.
 */
params ["_patient", "_released"];
private _current = _patient getVariable ["acme_sked_litter", objNull];
if (!local _patient || {!isNull _current && {_current isNotEqualTo _released}}) exitWith {};
detach _patient;
_patient setVariable ["acme_sked_loading", nil];
if (alive _patient) then {
    private _unconscious = _patient getVariable ["ACE_isUnconscious", false];
    private _anim = "unconscious";
    if (!_unconscious) then {
        _anim = "AmovPpneMstpSnonWnonDnon";
        if (!isNil "ACM_core_fnc_setLyingState") then {
            [_patient, true, true] call ACM_core_fnc_setLyingState;
            _anim = "ACM_LyingState";
        };
    };
    [_patient, _anim, 2] call ace_common_fnc_doAnimation;
};
[_patient, false] call acme_sked_fnc_hpmkSwap;
