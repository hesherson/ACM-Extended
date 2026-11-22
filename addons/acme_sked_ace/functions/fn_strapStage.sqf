/*
 * Server, when the timer of a strap-in starts and the casualty is laid on the litter: the straps of a litter
 * that has them as models of their own (the Talon, fn_strapArcs.sqf) are closed over the casualty one after
 * the other while the timer runs. A timer that is broken off opens them again (fn_request.sqf).
 * Arguments: 0: casualty, 1: laid out litter.
 */
params ["_patient", "_litter"];
if (!isServer || {isNull _litter}) exitWith {};
private _straps = count getArray (configOf _litter >> "acmeStrapArcBare");
if (_straps == 0) exitWith {};
private _token = (_litter getVariable ["acme_strap_stage", 0]) + 1;
_litter setVariable ["acme_strap_stage", _token];
private _seconds = getNumber (configFile >> "ace_medical_treatment_actions" >> "ACME_SKED_StrapIn" >> "treatmentTime");
for "_i" from 1 to _straps do {
    [{
        params ["_patient", "_litter", "_count", "_token"];
        if (isNull _litter || {isNull _patient} || {(_litter getVariable ["acme_strap_stage", 0]) != _token}
            || {(_patient getVariable ["acme_sked_placing", objNull]) isNotEqualTo _litter}
            || {(attachedTo _patient) isNotEqualTo _litter}) exitWith {};
        [_litter, (vest _patient) in ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"], _count] call acme_sked_fnc_strapArcs;
    }, [_patient, _litter, _i, _token], _seconds * _i / (_straps + 0.5)] call CBA_fnc_waitAndExecute;
};
