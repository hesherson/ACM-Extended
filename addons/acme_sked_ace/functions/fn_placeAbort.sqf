/*
 * Where the casualty is local: the timer of the strap action was broken off. They stay lying where they are
 * (on the litter, or on the way to it), free again, in the ACE pose for their state.
 * Arguments: 0: casualty, 1: laid out litter.
 */
params ["_patient", "_litter"];
if (!local _patient) exitWith {};
_patient setVariable ["acme_sked_placeToken", (_patient getVariable ["acme_sked_placeToken", 0]) + 1];
if (!isNull _litter && {(attachedTo _patient) isEqualTo _litter}) then {detach _patient;};
if (alive _patient && {isNull (_patient getVariable ["acme_sked_litter", objNull])}) then {
    private _anim = "unconscious";
    if !(_patient getVariable ["ACE_isUnconscious", false]) then {
        _anim = "AmovPpneMstpSnonWnonDnon";
        if (!isNil "ACM_core_fnc_setLyingState") then {
            [_patient, true, true] call ACM_core_fnc_setLyingState;
            _anim = "ACM_LyingState";
        };
    };
    [_patient, _anim, 2, true] call ace_common_fnc_doAnimation;
};
["ACME_headElev_transportUp", [_patient]] call CBA_fnc_localEvent;
