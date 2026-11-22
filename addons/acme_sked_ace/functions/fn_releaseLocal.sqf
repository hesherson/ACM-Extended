/*
 * Where the casualty is local: detach them from the SKED, put them in the ACE pose for their state, and
 * give back the unsqueezed HPMK-I shell (dead or alive).
 * Arguments: 0: casualty.
 */
params ["_patient", "_released", ["_gear", []]];
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
// (a casualty who is still wrapped in the HPMK-I stays undressed: his gear comes back when the shell comes off,
// ACME_fnc_hpmkDress)
if !((_patient getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"]
    && {(vest _patient) in ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"]}) then {
    [_patient, _gear] call acme_sked_fnc_gearShow;
};
[_patient, false] call acme_sked_fnc_hpmkSwap;
["ACME_headElev_transportUp", [_patient]] call CBA_fnc_localEvent;
