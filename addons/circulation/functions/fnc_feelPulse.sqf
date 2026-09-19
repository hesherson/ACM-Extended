/* B129 pulse palpation minigame.
 * Keeps ACME's token-safe pulse/watch/Escape lifecycle and Direct Pressure handoff,
 * while adding site-aware palpability plus hemodynamic pulse character. Thready
 * pulses are smaller/dimmer/narrower; bounding pulses are larger/brighter/broader.
 * Electrical activity without mechanical circulation never creates a palpated beat.
 */
params ["_medic","_patient","_bodyPart"];
if (isNull _medic || {isNull _patient}) exitWith {};

private _site = switch (toLowerANSI _bodyPart) do {
    case "head": {"carotid pulse"};
    case "leftarm";
    case "rightarm": {"radial pulse"};
    default {"femoral pulse"};
};

// Vehicle-safe path. Closing the medical dialog and forcing the kneeling pulse minigame while seated makes the
// engine immediately tear the interaction down. If both units share the same non-null vehicle, perform the same
// authoritative pulse read directly and leave the medical UI open. Different vehicle contexts remain out of reach.
private _medicVehicle = objectParent _medic;
private _patientVehicle = objectParent _patient;
if (!isNull _medicVehicle || {!isNull _patientVehicle}) exitWith {
    if (_medicVehicle isNotEqualTo _patientVehicle || {isNull _medicVehicle}) then {
        ["Patient is out of reach.", 1.5, _medic] call ace_common_fnc_displayTextStructured;
    } else {
        [_patient,"activity","%1 felt for a %2",[[_medic,false,true] call ace_common_fnc_getName,_site]] call ace_medical_treatment_fnc_addToLog;
        [_medic, _patient, _bodyPart] call ace_medical_treatment_fnc_checkPulseLocal;
    };
};

// Pulse-session generation. Old input hooks are retired synchronously, while an old PFH is allowed one final
// token-mismatch tick so it can release only its own treatment-pose token and old-patient Direct Pressure handoff.
// It is forbidden from clearing the shared cutRsc/watch state of the new pulse episode.
private _pulseEpoch = (uiNamespace getVariable ["ACME_PulseEpoch", 0]) + 1;
uiNamespace setVariable ["ACME_PulseEpoch", _pulseEpoch];
private _oldEsc = uiNamespace getVariable ["ACME_PulseEscKey", -1];
if (!(_oldEsc isEqualTo -1) && {!(_oldEsc isEqualTo "")}) then {[_oldEsc,"keydown"] call CBA_fnc_removeKeyHandler;};
private _oldMain = uiNamespace getVariable ["ACME_PulseEscDisplay", displayNull];
private _oldEscEH = uiNamespace getVariable ["ACME_PulseEscEH", -1];
if (!isNull _oldMain && {_oldEscEH >= 0}) then {_oldMain displayRemoveEventHandler ["KeyDown", _oldEscEH];};
private _oldWatch = uiNamespace getVariable ["ACME_PulseWatchCtrl", controlNull];
if (!isNull _oldWatch) then {ctrlDelete _oldWatch;};

[_patient,"activity","%1 felt for a %2",[[_medic,false,true] call ace_common_fnc_getName,_site]] call ace_medical_treatment_fnc_addToLog;
ace_medical_gui_pendingReopen = false;
if (dialog) then {closeDialog 0;};
"ACM_FeelPulse" cutRsc ["RscFeelPulse","PLAIN",0,false];
private _disp = uiNamespace getVariable ["ACM_FeelPulse",displayNull];
private _watch = controlNull;
if (!isNull _disp) then {
    (_disp displayCtrl 80001) ctrlSetText format ["%1 (%2)",[_patient,false,true] call ace_common_fnc_getName,_site];
    // Use the engine's watch control directly on the pulse layer. It does not create another display, so Escape
    // remains owned by this pulse check and cannot leave a watch UI behind.
    _watch = _disp ctrlCreate ["RscWatch", 80003];
    if (!isNull _watch) then {_watch ctrlShow true;};
};
uiNamespace setVariable ["ACME_PulseWatchCtrl", _watch];
uiNamespace setVariable ["ACME_PulseCheckActive",true];
uiNamespace setVariable ["ACME_PulseCheckEscape",false];
uiNamespace setVariable ["ACME_PulseCheckCancel",false];
uiNamespace setVariable ["ACME_PulseCheckMedic",_medic];
uiNamespace setVariable ["ACME_PulseCheckPatient",_patient];
uiNamespace setVariable ["ACME_PulseCheckStartedAt",CBA_missionTime];
uiNamespace setVariable ["ACME_PulseVisualNext",0];
private _poseEpoch = [_medic,"pulse",-1] call ACME_fnc_treatmentPoseStart;
uiNamespace setVariable ["ACME_PulsePoseEpoch",_poseEpoch];

// Consume Escape instead of letting the engine open the pause menu. The RscFeelPulse layer is a cutRsc, not a
// dialog, so the main display (46) must own the KeyDown as well as CBA's key handler.
private _mainDisplay = findDisplay 46;
private _escEH = -1;
if (!isNull _mainDisplay) then {
    _mainDisplay setVariable ["ACME_PulseKeyEpoch", _pulseEpoch];
    _escEH = _mainDisplay displayAddEventHandler ["KeyDown", {
        params ["_display", "_key"];
        private _epoch = _display getVariable ["ACME_PulseKeyEpoch", -1];
        if (_key != 1
            || {(uiNamespace getVariable ["ACME_PulseEpoch", -2]) != _epoch}
            || {!(uiNamespace getVariable ["ACME_PulseCheckActive", false])}) exitWith {false};
        uiNamespace setVariable ["ACME_PulseCheckEscape", true];
        true
    }];
};
private _escCode = compile format [
    "if ((uiNamespace getVariable ['ACME_PulseEpoch', -2]) != %1) exitWith {false}; if (uiNamespace getVariable ['ACME_PulseCheckActive', false]) then {uiNamespace setVariable ['ACME_PulseCheckEscape', true]; true} else {false};",
    _pulseEpoch
];
private _esc = [1,[false,false,false],_escCode,"keydown","",false,0] call CBA_fnc_addKeyHandler;
uiNamespace setVariable ["ACME_PulseEscKey",_esc];
uiNamespace setVariable ["ACME_PulseEscEH",_escEH];
uiNamespace setVariable ["ACME_PulseEscDisplay",_mainDisplay];

private _pfh = [{
    params ["_args","_pfh"];
    _args params ["_medic","_patient","_bodyPart","_esc","_poseEpoch","_pulseEpoch","_mainDisplay","_escEH"];

    // Superseded pulse check. Release only resources which belong to this captured patient/pose. If the replacement
    // pulse is the same provider on the same DP patient, leave TreatmentBusy asserted because the new pulse still
    // owns provider animation. No shared UI variables are cleared here.
    if ((uiNamespace getVariable ["ACME_PulseEpoch", -1]) != _pulseEpoch) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
        [_medic,"pulse",_poseEpoch] call ACME_fnc_treatmentPoseStop;
        private _newMedic = uiNamespace getVariable ["ACME_PulseCheckMedic", objNull];
        private _newPatient = uiNamespace getVariable ["ACME_PulseCheckPatient", objNull];
        private _sameReplacement = (uiNamespace getVariable ["ACME_PulseCheckActive", false])
            && {_newMedic isEqualTo _medic} && {_newPatient isEqualTo _patient};
        if (!_sameReplacement && {local _medic}
            && {_medic getVariable ["ACME_DP_Active", false]}
            && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
            _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
            _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
            _medic setVariable ["ACME_DP_InPose", false, false];
            _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
        };
    };

    private _uiGuardArmed = CBA_missionTime > ((uiNamespace getVariable ["ACME_PulseCheckStartedAt", CBA_missionTime]) + 0.20);
    private _menuOpen = _uiGuardArmed && {!isNull (uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull])};
    private _replacementDialog = _uiGuardArmed && {dialog};
    private _quit = isNull _medic || {isNull _patient} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious",false]}
        || {!(uiNamespace getVariable ["ACME_PulseCheckActive", false])}
        || {uiNamespace getVariable ["ACME_PulseCheckEscape",false]}
        || {uiNamespace getVariable ["ACME_PulseCheckCancel",false]}
        || {_menuOpen} || {_replacementDialog}
        || {_medic distance2D _patient > 4.5};
    if (_quit) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
        if ((uiNamespace getVariable ["ACME_PulsePFH", -2]) == _pfh) then {uiNamespace setVariable ["ACME_PulsePFH", -1];};
        [_esc,"keydown"] call CBA_fnc_removeKeyHandler;
        if ((uiNamespace getVariable ["ACME_PulseEscKey", -2]) == _esc) then {uiNamespace setVariable ["ACME_PulseEscKey", -1];};
        if (!isNull _mainDisplay && {_escEH >= 0}) then {_mainDisplay displayRemoveEventHandler ["KeyDown", _escEH];};
        if ((uiNamespace getVariable ["ACME_PulseEscEH", -2]) == _escEH) then {
            uiNamespace setVariable ["ACME_PulseEscEH", -1];
            uiNamespace setVariable ["ACME_PulseEscDisplay", displayNull];
        };

        private _escaped = uiNamespace getVariable ["ACME_PulseCheckEscape",false];
        private _watchCtrl = uiNamespace getVariable ["ACME_PulseWatchCtrl", controlNull];
        if (!isNull _watchCtrl) then {ctrlDelete _watchCtrl;};
        uiNamespace setVariable ["ACME_PulseWatchCtrl", controlNull];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
        uiNamespace setVariable ["ACME_PulseCheckActive",false];
        uiNamespace setVariable ["ACME_PulseCheckEscape",false];
        uiNamespace setVariable ["ACME_PulseCheckCancel",false];
        uiNamespace setVariable ["ACME_PulseCheckMedic",objNull];
        uiNamespace setVariable ["ACME_PulseCheckPatient",objNull];
        uiNamespace setVariable ["ACME_PulseCheckStartedAt",-1];
        uiNamespace setVariable ["ACME_PulseVisualNext",0];

        // End the pulse/stethoscope pose before handing animation ownership back to Direct Pressure. CheckPulse's
        // ACE success event deliberately leaves ACME_DP_TreatmentBusy set while this minigame is alive. Clearing it
        // any earlier lets the DP PFH reassert its hold over the pulse pose and makes Feel Pulse instantly disappear.
        [_medic,"pulse",_poseEpoch] call ACME_fnc_treatmentPoseStop;
        if (local _medic
            && {_medic getVariable ["ACME_DP_Active", false]}
            && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
            _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
            _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
            _medic setVariable ["ACME_DP_InPose", false, false];
            _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
        };
        if (_escaped) then {[_patient,"examine"] call ACME_fnc_reopenMedicalMenu;};
    };

    private _disp = uiNamespace getVariable ["ACM_FeelPulse",displayNull];
    if (isNull _disp) exitWith {};
    private _heart = _disp displayCtrl 80002;
    if (isNull _heart) exitWith {};

    private _profile = [_patient, _bodyPart] call ACME_fnc_pulsePerfusionProfile;
    _profile params ["_sitePalpable","_electricalHR","_hr","_strength","_character","_irregularity","_deficit","_bpSystolic","_bpDiastolic","_pulsePressure"];
    private _next = uiNamespace getVariable ["ACME_PulseVisualNext",0];

    if (_sitePalpable && {_hr > 0}) then {
        _heart ctrlShow true;

        if (CBA_missionTime >= _next) then {
            private _base = _heart getVariable ["ACME_PulseBase",ctrlPosition _heart];
            _heart setVariable ["ACME_PulseBase",_base];
            _base params ["_x","_y","_w","_h"];

            // Mechanical rate, not monitor rate. AFib and severe low-output tachycardia can therefore show a
            // pulse deficit while the electrical monitor continues to count every QRS.
            private _nominalDelay = 60 / (_hr max 1);
            private _jitter = if (_irregularity > 0) then {random [-_irregularity, 0, _irregularity]} else {0};
            private _delay = (_nominalDelay * (1 + _jitter)) max 0.16;

            private _thready = _character == "thready";
            private _bounding = _character == "bounding";
            private _scale = if (_thready) then {
                1.10 + (0.35 * _strength)
            } else {
                if (_bounding) then {2.15 + (0.35 * _strength)} else {1.45 + (0.55 * _strength)}
            };
            private _alpha = if (_thready) then {
                0.18 + (0.42 * _strength)
            } else {
                if (_bounding) then {1} else {0.58 + (0.42 * _strength)}
            };
            private _beatTime = if (_thready) then {
                0.08 min (0.18 * _delay)
            } else {
                if (_bounding) then {0.18 min (0.28 * _delay)} else {0.12 min (0.22 * _delay)}
            };
            private _releaseTime = if (_thready) then {
                0.11 min (0.24 * _delay)
            } else {
                if (_bounding) then {0.30 min (0.42 * _delay)} else {0.18 min (0.32 * _delay)}
            };

            private _cx = _x + (_w / 2);
            private _cy = _y + (_h / 2);
            _heart ctrlSetTextColor [1,0,0,_alpha];
            _heart ctrlSetPosition [_cx - (_w * _scale / 2), _cy - (_h * _scale / 2), _w * _scale, _h * _scale];
            _heart ctrlCommit _beatTime;

            [{
                params ["_ctrl","_basePos","_release","_releaseAlpha"];
                if (!isNull _ctrl) then {
                    _ctrl ctrlSetPosition _basePos;
                    _ctrl ctrlSetTextColor [1,0,0,_releaseAlpha];
                    _ctrl ctrlCommit _release;
                };
            }, [_heart,_base,_releaseTime,(_alpha * (if (_thready) then {0.45} else {0.72}))], _beatTime] call CBA_fnc_waitAndExecute;

            uiNamespace setVariable ["ACME_PulseVisualNext",CBA_missionTime + _delay];
        };
    } else {
        _heart ctrlShow false;
    };
},0,[_medic,_patient,_bodyPart,_esc,_poseEpoch,_pulseEpoch,_mainDisplay,_escEH]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_PulsePFH", _pfh];
