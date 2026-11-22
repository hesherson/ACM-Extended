/*
 * Where the casualty is local: pose them (lying on the back, from the setting) and place them in the SKED.
 * Placement is measured from the casualty's own body (pelvis, head, shoulders, chest), so it does not
 * depend on how the pose sits in the unit's model space; a second pass corrects what is left over.
 * Arguments: 0: casualty, 1: SKED.
 */
params ["_patient", "_litter"];
if (!local _patient || {isNull _litter}) exitWith {};
if ((_patient getVariable ["acme_sked_litter", objNull]) isNotEqualTo _litter) exitWith {};
// Lower supported Semi-Fowler first, including its existing carrier custody and collision cleanup.
if (_patient getVariable ["ACME_headElevated", false]) then {
    ["ACME_headElev_transportDown", [_patient]] call CBA_fnc_localEvent;
};
// A casualty who was laid on the litter during the timer is in the pose already and only changes litter.
private _pose = [_patient, _litter] call acme_sked_fnc_patientPose;
private _posed = (toLowerANSI animationState _patient) == (toLowerANSI _pose);
if (alive _patient && {!_posed}) then {
    [_patient, _pose, 2, true] call ace_common_fnc_doAnimation;
};
_patient setVariable ["acme_sked_placeToken", (_patient getVariable ["acme_sked_placeToken", 0]) + 1];
[_patient, _litter] call acme_sked_fnc_gearHide;
if (_posed || {!alive _patient}) exitWith {
    [_patient, _litter, false] call acme_sked_fnc_align;
    ["patient aligned", _litter, _patient, [attachedTo _patient]] call acme_sked_fnc_traceTransport;
    [_patient] call acme_sked_fnc_poseGuard;
};
[{
    params ["_patient", "_litter"];
    if (!local _patient || {isNull _litter} || {!isNull objectParent _patient}
        || {_patient getVariable ["acme_sked_loading", false]}
        || {!((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter)}) exitWith {};
    [_patient, _litter, false] call acme_sked_fnc_align;
    [{
        params ["_patient", "_litter"];
        if (!local _patient || {isNull _litter} || {!isNull objectParent _patient} || {_patient getVariable ["acme_sked_loading", false]} || {!((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter)}) exitWith {};
        [_patient, _litter, true] call acme_sked_fnc_align;
        ["patient aligned", _litter, _patient, [attachedTo _patient]] call acme_sked_fnc_traceTransport;
        [_patient] call acme_sked_fnc_poseGuard;
    }, [_patient, _litter], 0.3] call CBA_fnc_waitAndExecute;
}, [_patient, _litter], 0.8] call CBA_fnc_waitAndExecute;
