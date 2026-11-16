/*
 * Where the casualty is local: pose them (lying on the back, from the setting) and place them in the SKED.
 * Placement is measured from the casualty's own body (pelvis, head, shoulders, chest), so it does not
 * depend on how the pose sits in the unit's model space; a second pass corrects what is left over.
 * Arguments: 0: casualty, 1: SKED.
 */
params ["_patient", "_litter"];
if (!local _patient || {isNull _litter}) exitWith {};
if (alive _patient) then {
    [_patient, missionNamespace getVariable ["acme_sked_patientAnim", "unconsciousfaceup"], 2] call ace_common_fnc_doAnimation;
};
[{
    params ["_patient", "_litter"];
    if (isNull _litter || {!((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter)}) exitWith {};
    [_patient, _litter, false] call acme_sked_fnc_align;
    [{
        params ["_patient", "_litter"];
        if (isNull _litter || {!((_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter)}) exitWith {};
        [_patient, _litter, true] call acme_sked_fnc_align;
        [_patient] call acme_sked_fnc_poseGuard;
    }, [_patient, _litter], 0.3] call CBA_fnc_waitAndExecute;
}, [_patient, _litter], 0.8] call CBA_fnc_waitAndExecute;
