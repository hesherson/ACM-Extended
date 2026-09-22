// drop a patient unconscious, if they are not already, and collapse them into the ACE unconscious ragdoll. it is
// Standing patients collapse at onset. Already-down patients keep their current pose and start the spasm layer. it runs where the patient is local, because the lido tick is local to the patient.
// call it as [_patient] call ACME_fnc_seizureCollapse.
params ["_patient"];
if (isNull _patient || {!alive _patient} || {!local _patient}) exitWith {};

// head elevation is sacred. a head-elevated casualty must stay elevated through a seizure, because the elevation is
// only ever removed by another person, through lower head or a maneuver that suspends it, and never by the
// seizure of the patient.
// so for an elevated patient we do not suspend the elevation and do not ragdoll them out of the pose. The
// GestureSpasm seizure layer can run without changing the patient's heading or tearing down the elevation hold.
// we still knock them unconscious if they are somehow awake, and we hold the elevated pose right after, so the
// unconscious-collapse of the engine does not drop them out of it.
private _headElevated = _patient getVariable ["ACME_headElevated", false];

// put them into the medical unconscious state if they are somehow still awake, because a generalized seizure
// abolishes consciousness. it is almost always a no-op here, because a lidocaine-toxic patient on a running drip
// is already down.
private _wasUncon = _patient getVariable ["ACE_isUnconscious", false];
if (!_wasUncon) then {
    // Use ACE's canonical transition so seizure onset cannot split the raw flag from the medical state machine.
    [_patient, true, 0, false] call ace_medical_fnc_setUnconscious;
};

if (_headElevated) then {
    // re-assert the elevated hold a beat after any knockout ragdoll, so a patient who was knocked out by the seizure
    // onset is not left flat: the elevation attachment and pose are restored and they stay reclined, seizing.
    if (!_wasUncon) then {
        [{
            params ["_p"];
            if (!isNull _p && {_p getVariable ["ACME_headElevated", false]} && {!(_p getVariable ["ACME_headElev_Suspended", false])}) then {
                [_p] call ACME_fnc_headElevApplyTilt;
            };
        }, [_patient], 0.4] call CBA_fnc_waitAndExecute;
    };
};
// Already unconscious: preserve supine/prone/head-elevated placement. An extra collapse would
// replace the patient's posture before the first spasm, including during a debug-induced seizure.

// an OPA cannot stay seated against a clenching, convulsing jaw, so it is expelled at seizure onset. an i-gel or
// SGA, at the oral slot value "SGA", and a nasal NPA are more secure and stay put, so only an actual OPA is
// cleared.
if (!(_patient getVariable ["ACME_roc_paralyzed", false]) && {(_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "OPA"}) then {
    [_patient, "", true] call ACM_airway_fnc_setOralAirwayItem;
};
