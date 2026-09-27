/* The provider has entered its authored reach. Only this placement may now move the casualty. */
params ["_medic", "_patient", "_mode", "_poseToken", ["_cancel", false]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevMedicReady", _this] call ACME_fnc_ownerDispatch;};
if (!alive _patient || {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken}
    || {!(_patient getVariable ["ACME_headElevated", false])}
    || {_patient getVariable ["ACME_headElev_Suspended", false]}) exitWith {};
private _validMedic = !isNull _medic && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {(objectParent _medic) isEqualTo (objectParent _patient)}
    && {(_patient distance2D _medic) <= (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])};
if (_mode == "elevate") exitWith {
    if ((_patient getVariable ["ACME_headElev_pendingLift", []]) isNotEqualTo [_medic, _poseToken]) exitWith {};
    _patient setVariable ["ACME_headElev_pendingLift", [], true];
    if (_cancel || {!_validMedic}) exitWith {
        [objNull, _patient, true] call ACME_fnc_headElevateStop;
    };
    [_patient] call ACME_fnc_headElevApplyTilt;
};
if (_mode == "lower" && {!_cancel} && {_validMedic}) then {
    [_medic, _patient, false, true, false, true] call ACME_fnc_headElevateStop;
};
