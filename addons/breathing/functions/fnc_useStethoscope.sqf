/*
 * Author: Blue
 * Handle using stethoscope on chest.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget] call ACM_breathing_fnc_useStethoscope;
 *
 * Public: No
 */

params ["_medic", "_patient", ["_bodyPart", "Body"]];

// you cannot auscultate in an airframe.
// this is not a balance decision, it is simply true, and every flight medic knows it. a running helicopter puts 500
// to 2000 hz of transmission and gear-mesh noise straight through the structure, right on top of the frequencies
// breath sounds live in. you are not listening to a quiet chest through a stethoscope, you are listening to a
// gearbox. crews do not even try: they go to what they can see and measure, meaning the chest rise, the EtCO2, the
// SpO2 and the numbers of the ventilator.
// the refusal is the lesson: the tools you leaned on in the aid station do not all come with you, and the ones that
// do are the ones with a screen.
// the exitwith is top-level on purpose. nested inside an if or else it would only exit the inner block and the
// stethoscope would carry on working regardless, which is exactly the sort of silent no-op that is impossible to
// spot from the outside.
private _mVeh = vehicle _medic;
if ((missionNamespace getVariable ["ACME_flightNoise_enable", true])
    && {_mVeh != _medic}
    && {_mVeh isKindOf "Air"}
    && {isEngineOn _mVeh}) exitWith {
    ["Cannot auscultate: airframe noise. Use EtCO2, SpO2 and chest rise.", 3, _medic] call ace_common_fnc_displayTextStructured;
};

[_patient, "activity", "STR_ACM_breathing_Stethoscope_ActionLog", [[_medic, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;

[[_medic, _patient, _bodyPart], {  // on start.
    params ["_medic", "_patient", "_bodyPart"];

    [_patient,"stethoscopeLungs",[[_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;

    // Auscultation gets one owner-authoritative patient pose lease for the whole scope session. Elevated and
    // otherwise downed casualties are held directly in the normal face-up rest. There is deliberately no
    // roll-to-back transition here: head elevation already ran its authored lowering sequence before this dialog
    // opened, and an ordinary downed casualty can go straight to the supine rest without the sideways roll theatre.
    // A conscious upright casualty who was not already positioned is not forced to the ground.
    private _lyingRaw = _patient getVariable ["ACM_core_Lying_State", false];
    private _lying = if (_lyingRaw isEqualType true) then {_lyingRaw} else {_lyingRaw > 0};
    private _needsSupine = (_patient getVariable ["ACE_isUnconscious", false])
        || {_patient getVariable ["ace_medical_unconscious", false]}
        || {_lying}
        || {_patient getVariable ["ACME_headElevated", false]}
        || {_patient getVariable ["ACME_headElev_Suspended", false]}
        || {(stance _patient) == "PRONE"};
    if (_needsSupine && {isNull objectParent _patient}) then {
        private _serial = (missionNamespace getVariable ["ACME_stethPatientAnimSerial", 0]) + 1;
        missionNamespace setVariable ["ACME_stethPatientAnimSerial", _serial];
        private _token = format ["steth:%1:%2:%3:%4", clientOwner, netId _medic, netId _patient, _serial];
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"];
        private _anim = ["", _faceUp] select ((toLowerANSI animationState _patient) != (toLowerANSI _faceUp));
        [_patient, _anim, 2, "stethoscope", _medic, 1.6, 4, _token] call ACME_fnc_patientAnimRequest;
        _medic setVariable ["ACME_stethPatientAnimLease", [_patient, _token, CBA_missionTime + 0.65], false];
    } else {
        _medic setVariable ["ACME_stethPatientAnimLease", [], false];
    };

    // Reduce surrounding audio while the scope is in use. Diagnostic channels bypass this mix.
    ace_hearing_volumeAttenuation = 0.1;
    [(localize "STR_ACE_Volume_Lowered"), 1.5, _medic] call ace_common_fnc_displayTextStructured;

    createDialog "ACM_breathing_Stethoscope_Dialog";

    uiNamespace setVariable ["ACM_breathing_Stethoscope_DLG",(findDisplay 81000)];

    private _display = uiNamespace getVariable ["ACM_breathing_Stethoscope_DLG", displayNull];
    [_display] call ACME_fnc_stethoscopeInit;
    private _ctrlText = _display displayCtrl 81001;
    _ctrlText ctrlSetText format ["%1 (%2)", [_patient, false, true] call ace_common_fnc_getName, (localize "STR_ACE_medical_gui_Torso")];
}, {  // on cancel.
    params ["_medic", "_patient", "_bodyPart"];

    // Release only this provider's animation token. A second provider auscultating the same casualty keeps their
    // own lease and therefore cannot be interrupted by this dialog closing.
    private _lease = _medic getVariable ["ACME_stethPatientAnimLease", []];
    if ((count _lease) >= 2) then {
        private _leasePatient = _lease param [0, objNull];
        private _leaseToken = _lease param [1, ""];
        if (!isNull _leasePatient && {_leaseToken != ""}) then {
            [_leasePatient, _leaseToken] call ACME_fnc_patientAnimRelease;
        };
    };
    _medic setVariable ["ACME_stethPatientAnimLease", [], false];

    if !(isNull findDisplay 81000) then {
        closeDialog 0;
    };

    ["STR_ACM_breathing_Stethoscope_Stopped", 1.5, _medic] call ace_common_fnc_displayTextStructured;

    [-1] call ace_hearing_fnc_updateHearingProtection;
}, {  // per frame.
    params ["_medic", "_patient", "_bodyPart"];

    // CPR is a higher-order chest maneuver. If another provider starts compressions, retire auscultation instead
    // of letting the two procedures fight over the patient.
    if ([_patient] call ACM_core_fnc_cprActive) exitWith {
        ACM_core_ContinuousAction_Active = false;
    };

    // Refresh the lease without replaying an animation when the casualty is already face-up. This is the critical
    // multiplayer guard: repeated providers may request the same posture, but only the current owner token can
    // refresh it, and no 0.6-second animation restart loop is created under the auscultation camera.
    private _lease = _medic getVariable ["ACME_stethPatientAnimLease", []];
    if ((count _lease) >= 3 && {CBA_missionTime >= (_lease param [2, 0])}) then {
        private _leasePatient = _lease param [0, objNull];
        private _leaseToken = _lease param [1, ""];
        if (!isNull _leasePatient && {_leasePatient isEqualTo _patient} && {_leaseToken != ""}) then {
            private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"];
            private _anim = ["", _faceUp] select ((toLowerANSI animationState _patient) != (toLowerANSI _faceUp));
            [_patient, _anim, 2, "stethoscope", _medic, 1.6, 4, _leaseToken] call ACME_fnc_patientAnimRequest;
            _lease set [2, CBA_missionTime + 0.65];
            _medic setVariable ["ACME_stethPatientAnimLease", _lease, false];
        };
    };

    [_patient] call ACME_fnc_stethoscopeTick;
}, false, 81000] call ACME_fnc_beginStethoscopeAction;
