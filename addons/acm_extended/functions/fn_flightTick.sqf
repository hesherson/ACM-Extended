/* One owner-local writer for altitude pressure, oxygen diagnostics and flight
 * maneuver effects. Enrollment is shared 1 Hz discovery; the hot worker never
 * scans all units or enrolls healthy flight occupants into clinical maintenance.
 * Native oxygenation reads live exposure independently, so first exposure does
 * not depend on a previous injury or on discovery having published a sample. */
private _patients = (missionNamespace getVariable ["ACME_flight_activePatients", []]) arrayIntersect
    (missionNamespace getVariable ["ACME_flight_activePatients", []]);
private _kept = [];
{
    private _patient = _x;
    if (isNull _patient || {!local _patient} || {!alive _patient}
        || {!(_patient isKindOf "CAManBase")}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}) then {continue};
    // Removing the exit marker before the tick guarantees a finite final pass.
    _patient setVariable ["ACME_flight_tickActive", false, false];
    [_patient] call ACME_fnc_altitudeTick;

    // ACE normally optimizes untouched AI out of native vitals. Activate its
    // existing worker only when this actual exposure lowers the oxygen ceiling.
    // The native event sets the flag synchronously, so stable exposure emits one
    // activation rather than a periodic event or a second oxygen integrator.
    private _ceiling = [_patient] call ACME_fnc_altitudeOxygenCeiling;
    if (_ceiling < 99 && {!(_patient getVariable ["ace_medical_medicalActivity",
        missionNamespace getVariable ["ace_medical_const_medicalActivity", false]])}) then {
        ["ace_medical_activateMedical", _patient] call CBA_fnc_localEvent;
    };
    if ([_patient, false] call ACME_fnc_flightNeedsTick) then {
        _kept pushBack _patient;
        _patient setVariable ["ACME_flight_tickActive", true, false];
    } else {
        // Approximate publication may suppress a final sub-epsilon step. Send
        // exact neutral values before retirement so remote BP/diagnostics cannot
        // retain the last tiny maneuver or hypoxia effect indefinitely.
        [_patient, "ACME_alt_hypoxia", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_alt_expanding", false] call ACME_fnc_setVarNet;
        // The exposed-pressure mirror also enrolls preoxygenation maintenance.
        // At final retirement there is no clinical altitude effect; leave that
        // mirror neutral while ambientRatio retains the measured atmosphere.
        // Oxygen calculations use live exposure, and existing PTX does not
        // retire here while its low-altitude pressure observations are needed.
        [_patient, "ACME_alt_pRatio", 1] call ACME_fnc_setVarNet;
        [_patient, "ACME_flightG_stress", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_flightG_resistAdd", 0] call ACME_fnc_setVarNet;
        // A future flight starts a new pressure baseline and clock. No altitude
        // travel during an idle interval is replayed on re-entry or teleport.
        {
            _patient setVariable [_x, nil, false];
        } forEach ["ACME_alt_ptxSample", "ACME_alt_tickStamp",
            "ACME_clock_altitude", "ACME_clock_altitude_owner"];
    };
} forEach _patients;
ACME_flight_activePatients = _kept;
