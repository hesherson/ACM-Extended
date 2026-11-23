/* B393: a casualty sitting up (Semi-Fowler) whose owner changed (his client left, the server handed him on). The
 * old owner's timers died with it: a pending sit-up after a treatment, the watch, the lift callbacks. On the new
 * owner, from the public state alone:
 *  - treatment leases of providers who are gone or dead no longer hold him flat;
 *  - laid flat for a treatment that has ended (no lease left): he sits up again;
 *  - sitting up but shown in another pose here (the lift tail was cut): the sitting pose, unless a provider's
 *    animation lease holds his body or he is wrapped in the HPMK (its pose is his then).
 * [_patient] call ACME_fnc_headElevTakeOver, where he is local. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {};
private _leases = _patient getVariable ["ACME_headElev_treatments", createHashMap];
if !(_leases isEqualType createHashMap) then {_leases = createHashMap;};
private _gone = (keys _leases) select {
    private _medic = (_leases get _x) param [0, objNull];
    isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
};
if (_gone isNotEqualTo []) then {
    {_leases deleteAt _x;} forEach _gone;
    _patient setVariable ["ACME_headElev_treatments", _leases, true];
};
private _token = _patient getVariable ["ACME_headElev_poseToken", ""];
if (_patient getVariable ["ACME_headElev_Suspended", false]) then {
    if (count _leases == 0) then {
        _patient setVariable ["ACME_headElev_ResumePending", true, true];
        [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], 1] call CBA_fnc_waitAndExecute;
    };
} else {
    if (!(_patient getVariable ["ACME_headElev_noAnimation", false])
        && {missionNamespace getVariable ["ACME_interventionAnimations", true]}
        && {isNull objectParent _patient} && {isNull attachedTo _patient}
        && {!((_patient getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"])}
        && {!([_patient] call ACME_fnc_patientAnimHeld)}
        && {(toLowerANSI animationState _patient) != "acme_headelevpatienthold"}) then {
        [_patient, "ACME_HeadElevPatientHold", 2] call ace_common_fnc_doAnimation;
    };
};
