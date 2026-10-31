/* B223: patient owner derives the physical interface from the attached device's settings.
   Never acquires equipment, consumes an item, starts power or removes a secured airway.
   The normal NIV eligibility/circuit alarm remains responsible for unsuitable patients. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _mask = (_patient getVariable ["ACME_vent_onPatient", false])
    && {_patient getVariable ["ACME_vent_circuit", false]}
    && {(_patient getVariable ["ACME_vent_custodyId", ""]) != ""}
    && {!(_patient getVariable ["ACME_vent_recovering", false])}
    && {[_patient] call ACME_fnc_ventMaskSelected};
if !(_mask isEqualTo (_patient getVariable ["ACME_vent_nivMask", false])) then {
    [_patient, "ACME_vent_nivMask", _mask] call ACME_fnc_setVarNet;
    if (_mask) then {
        // No residual mandatory/manual breaths may bridge into non-invasive operation.
        _patient setVariable ["ACME_vent_manualBreathTimes", [], false];
        _patient setVariable ["ACME_vent_simpleManualVolumes", [], false];
        [_patient, "ACME_vent_manualRR", 0] call ACME_fnc_setVarNet;
    };
};
_mask
