#include "..\script_component.hpp"
/* ACM Extended treatment bridge.
 * ACME owns only provider preflight, requested intervention-specific gestures, and the ventilator connector.
 * Native ACM/ACE remains authoritative for treatment timing, inventory, callbacks, cancellation and patient state.
 */
params ["_medic", "_patient", "_bodyPart", "_classname"];

// B190: the exposed HPMK overlay represents a physically open chest. CPR must execute as the canonical Body
// treatment even if the medical-menu overlay retained another exposed selection when the button was pressed.
if ((toLowerANSI _classname) == "cpr"
    && {!isNull _patient}
    && {(_patient getVariable ["ACME_hpmk_state", ""]) == "exposed"}) then {
    _bodyPart = "Body";
    _this set [2, _bodyPart];
};

private _medicVehicle = objectParent _medic;
private _sameVehicleTreatment = !isNull _medicVehicle && {(objectParent _patient) isEqualTo _medicVehicle};
private _interactionChecks = [["isNotInside", "isNotSwimming", "isNotInZeus"], ["isNotSwimming", "isNotInZeus"]] select _sameVehicleTreatment;
private _rangeOkay = _sameVehicleTreatment || {(_medic distance _patient) <= ace_medical_gui_maxDistance};

// Head positioning is provider theatre, never a global treatment lock. Any newly accepted medical click preempts
// a leftover/current Semi-Fowler provider sequence before normal treatment gating runs. Manual unsupported
// Semi-Fowler is also an active hands-on maneuver by design; a new intervention cancels that exact hold so a stale
// continuous-action generation can never leave the rest of the medical menu inert.
if (!isNull _medic && {local _medic} && {hasInterface} && {[_medic] call ace_common_fnc_isPlayer}) then {
    // Continuous-action recovery belongs to its recorded controller, never the incoming medic.
    // The shared controller keeps exclusivity until its own cancellation path has released the old action.
    if (_medic getVariable ["ACME_headElev_seqActive", false]) then {
        call ACME_fnc_headElevateCancelSeq;
    };

    // Non-dialog continuous hands-on holds are cancelled by the medical-menu-open event before buttons become
    // interactive. Do not clear them again here: starting a successor treatment in the same frame could increment
    // the continuous-action epoch before the old PFH runs its onCancel callback, leaking the old patient reservation.
};

// This debug command has no physical treatment or provider animation. Execute directly,
// so empty-hands preflight, the progress bar and the generic patient settle cannot consume the click.
if (_classname == "ACME_DebugInduceSeizure") exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !((toLowerANSI _bodyPart) == "head" && {[] call ACME_fnc_debugEnabled}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
    [_patient, "debugSeizure", [_medic, _patient]] call ACME_fnc_ownerDispatch;
    true
};

// Direct Pressure is an immediate medical-menu state toggle, not an ACE timed treatment. Running it through the
// normal treatment pipeline closes the medical menu for the progress dialog and invokes the generic weapon/stance
// preflight before callbackSuccess. Apply/Stop therefore execute here and repaint the existing menu in place.
private _fnc_refreshDirectPressureMenu = {
    params ["_m", "_p"];
    if (!hasInterface || {!local _m} || {!([_m] call ace_common_fnc_isPlayer)}) exitWith {};
    ace_medical_gui_pendingReopen = false;
    [{
        params ["_patient"];
        private _display = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
        if (!isNull _display
            && {(missionNamespace getVariable ["ace_medical_gui_target", objNull]) isEqualTo _patient}
            && {!isNil "ace_medical_gui_fnc_updateActions"}) then {
            [_display] call ace_medical_gui_fnc_updateActions;
        };
    }, [_p]] call CBA_fnc_execNextFrame;
};

if (_classname == "ACME_DirectPressure") exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};

    // Request acceptance is asynchronous. A queued request is a handled click even before its ACK activates
    // pressure; the accepted ACK owns the one-shot sound, so rejected clicks neither broadcast nor play twice.
    private _requested = [_medic, _patient, _bodyPart] call ACME_fnc_directPressureStart;
    [_medic, _patient] call _fnc_refreshDirectPressureMenu;
    _requested
};

// Stop Direct Pressure is state teardown, not a new treatment. It must never depend on a progress bar, provider
// weapon state, animation state, or another canTreat pass. If the button is visible for the held patient, clicking
// it releases pressure immediately.
if (_classname == "ACME_StopDirectPressure") exitWith {
    if (isNull _medic || {!local _medic}) exitWith {false};
    if (!(_medic getVariable ["ACME_DP_Active", false])
        || {!((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient)}) exitWith {false};
    [false, _medic] call ACME_fnc_directPressureStop;
    [_medic, _patient] call _fnc_refreshDirectPressureMenu;
    true
};

if !([_medic, _classname] call ACME_fnc_procedureActionAllowed) exitWith {false};

// Stable B182: manual carrier removal/replacement is an immediate equipment-state toggle, not a timed treatment.
// Do not close the menu, start a progress bar, holster the provider or enter chest-access animation.
if (_classname in ["ACME_ManualRemovePlateCarrier", "ACME_ManualReplacePlateCarrier"]) exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};

    private _restore = _classname == "ACME_ManualReplacePlateCarrier";
    ace_medical_gui_pendingReopen = false;
    [_patient, "manualPlateCarrier", [_medic, _patient, _restore]] call ACME_fnc_ownerDispatch;
    true
};

// Opening a shared workspace must not wait for a free kneeling/holster animation.
// Each actual intervention inside the panel retains its own checks and animation.
if (_classname in [
    "ACME_ApplyChestSeal", "ACME_PerformNARSPEAR", "ACME_VentOpenPatient",
    "ACME_PerformThoracostomy", "ACME_AdjustThoracostomy", "ACME_InsertChestTube"
]) exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
    if !([_medic, _patient, _interactionChecks] call ace_common_fnc_canInteractWith) exitWith {false};
    if (!_rangeOkay) exitWith {false};

    // Modal procedure launchers are not ACE timed treatments. Their panel/preparation controller owns provider
    // animation, cancellation and medical-menu return. Running thoracostomy through the generic treatment preflight
    // left setUnitPos/weapon-away/native-rate state alive underneath the chest-access provider and let ACE reopen the
    // medical menu over the preparation sequence.
    ace_medical_gui_pendingReopen = false;
    if (_classname == "ACME_VentOpenPatient") then {
        [_patient] call ACME_fnc_ventPanelOpen;
    } else {
        if (_classname in ["ACME_PerformThoracostomy", "ACME_AdjustThoracostomy", "ACME_InsertChestTube"]) then {
            [_medic, _patient, _bodyPart] call ACME_fnc_thoraOpen;
        } else {
            [_medic, _patient, _bodyPart, ["seal", "spear"] select (_classname == "ACME_PerformNARSPEAR")] call ACME_fnc_chestSealOpen;
        };
    };
    true
};

if (_classname != "ACME_ConnectETVent") exitWith {
    // Preserve ACM/ACE cursor-menu deferral before ACME starts its one-shot stance/weapon preflight.
    if (uiNamespace getVariable ["ace_interact_menu_cursorMenuOpened", false]) exitWith {
        [ace_medical_treatment_fnc_treatment, _this] call CBA_fnc_execNextFrame;
        true
    };

    // Direct Pressure may coexist with ordinary treatments, but its held provider pose must never block the
    // treatment wrapper's own empty-hands preflight.  Track whether this treatment is acting on the same casualty.
    private _dpSamePatient = !isNull _medic
        && {_medic getVariable ["ACME_DP_Active", false]}
        && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient};

    private _fnc_dpPauseForManeuver = {
        params ["_m", "_classKey"];
        if (isNull _m || {!local _m} || {!(_m getVariable ["ACME_DP_Active", false])}) exitWith {};
        _m setVariable ["ACME_DP_Paused", true, false];
        _m setVariable ["ACME_DP_PauseTreatmentClass", _classKey, false];
        // Retire the looping DP pose immediately.  The incoming maneuver owns provider animation until it ends.
        _m setVariable ["ACME_dah_gen", (_m getVariable ["ACME_dah_gen", 0]) + 1, false];
        _m setVariable ["ACME_DP_InPose", false, false];
        _m setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
        _m setVariable ["ACME_DP_LastPoseAssert", 0, false];
    };

    // BVM uses ACM's treatment path. Its accepted start releases this provider's
    // Direct Pressure hold before taking over input and animation.
    private _nativeContinuousClass = toLowerANSI _classname;
    if (_medic getVariable ["ACME_chestAccessPreflightActive", false]) exitWith {false};

    // Chest-access preparation is a physical gear transaction around the real treatment:
    // lay Semi-Fowler flat if needed, lift the casualty, remove/park the carrier, lower supine, then launch
    // native ACM treatment ONCE. It never reserves or edits ContinuousAction state and never recursively calls
    // the generic treatment wrapper, so presentation failure cannot consume the clinical click.
    private _chestClasses = missionNamespace getVariable ["ACME_chestAccess_classes", []];
    private _maneuverClasses = missionNamespace getVariable [
        "ACME_chestAccess_maneuverClasses",
        ["cpr","usebvm","usebvm_oxygen","usebvm_vehicleoxygen","usebvm_portableoxygen"]
    ];
    private _needsChestAccess = _nativeContinuousClass in _chestClasses;
    private _chestSaved = +(_patient getVariable ["ACME_chestAccess_vestLoadout", []]);
    private _existingChest = _medic getVariable ["ACME_chestAccess_treatment", []];
    private _existingChestClass = _existingChest param [1,""];
    private _existingChestId = _existingChest param [2,""];
    private _sameManeuverFamily = (_nativeContinuousClass in _maneuverClasses)
        && {_existingChestClass in _maneuverClasses};
    private _alreadyPrepared = ((_existingChest param [0,objNull]) isEqualTo _patient)
        && {_existingChestId != ""}
        && {_existingChestClass == _nativeContinuousClass || {_sameManeuverFamily}};
    private _actualChestSide = [_patient, _patient getVariable ["ACME_CS_facing","front"]] call ACME_fnc_chestSealActualSide;
    // Both assessments declare ACM_rollToBack. Inspect Chest keeps its native no-carrier path; Check Breathing
    // explicitly enters the held preparation below, whose patient transaction also normalizes posture.
    private _nativeRollOwnsPosition = _nativeContinuousClass in ["checkbreathing", "acme_inspectchest"];
    private _needsFrontNormalize = !_nativeRollOwnsPosition
        && {alive _patient}
        && {isNull objectParent _patient}
        && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll}
        && {_actualChestSide == "back"};
    private _bvmChestClass = _nativeContinuousClass in ["usebvm","usebvm_oxygen","usebvm_vehicleoxygen","usebvm_portableoxygen"];
    // A previous CPR/BVM stop can still own the casualty through the reverse carrier lift. Do not start a new
    // clinical maneuver underneath that patient animation merely because the carrier is temporarily still off.
    private _chestBusy = _patient getVariable ["ACME_chestAccess_vestBusy", ""];
    private _restoreInFlight = (_chestBusy find "restore:access:") == 0;
    private _needsPhysicalPrep = _restoreInFlight
        || {_needsFrontNormalize}
        || {((vest _patient) != "" && {(count _chestSaved) != 2})}
        || {!_bvmChestClass
            && {_patient getVariable ["ACME_headElevated", false]}
            && {!(_patient getVariable ["ACME_headElev_Suspended", false])}};

    // Check Breathing owns one frozen chest-access episode, including patients without a carrier.
    // Its native three-second timer starts only after this episode reaches its held frame.
    private _heldBreathingCheck = _nativeContinuousClass == "checkbreathing"
        && {isNull objectParent _medic} && {_medic isNotEqualTo _patient};
    if (_needsChestAccess && {_needsPhysicalPrep || {_heldBreathingCheck}} && {!_alreadyPrepared}
        && {local _medic} && {!isNull _medic} && {alive _medic}) exitWith {
        if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
        if !([_medic, _patient, _interactionChecks] call ace_common_fnc_canInteractWith) exitWith {false};
        if (!_rangeOkay) exitWith {false};
        // One accepted click owns this preparation generation. A closed menu plus this flag makes repeated clicks no-ops.
        if (_medic getVariable ["ACME_chestAccessPreflightActive", false]) exitWith {false};

        private _serial = (missionNamespace getVariable ["ACME_chestAccess_serial", 0]) + 1;
        missionNamespace setVariable ["ACME_chestAccess_serial", _serial];

        // CPR/BVM swaps reuse one maneuver-family lease instead of tearing down/reacquiring carrier custody.
        private _leaseId = if (_sameManeuverFamily && {_existingChestId != ""}) then {
            _existingChestId
        } else {
            format ["%1:%2:%3", clientOwner, netId _medic, _serial]
        };
        private _token = format ["chestprep:%1:%2:%3", clientOwner, netId _medic, _serial];
        private _args = +_this;

        // Direct Pressure remains clinically alive but becomes animation-passive before the first carrier frame.
        if (_dpSamePatient) then {[_medic, _nativeContinuousClass] call _fnc_dpPauseForManeuver;};

        _medic setVariable ["ACME_chestAccessPreflightActive", true, false];
        _medic setVariable ["ACME_chestAccessPreflightToken", _token, false];
        _medic setVariable ["ACME_chestAccessPreflightCancel", false, false];
        _medic setVariable ["ACME_checkBreathingProviderRequested", "", false];
        _medic setVariable ["ACME_chestAccess_treatment", [_patient, _nativeContinuousClass, _leaseId]];
        if (_heldBreathingCheck) then {
            diag_log format ["[ACME CHECK BREATHING] preparing patient %1; build %2; lease %3",
                netId _patient, missionNamespace getVariable ["ACME_buildBatch","?"], _leaseId];
        };

        // The medical menu closes on the accepted click. Its normal pending-reopen handler is suppressed by the
        // renderer while this flag is active; only an explicit abort/failure reopens it.
        ace_medical_gui_pendingReopen = false;
        if (dialog) then {closeDialog 0;};
        [true, _medic, _patient, _token] call ACME_fnc_chestAccessPreparing;

        // Escape and F0 cancel preparation, not the next intervention. Handler IDs are generation-local strings.
        private _cancelCode = compile format [
            "private _m=objectFromNetId '%2'; if (!isNull _m && {local _m} && {(_m getVariable ['ACME_chestAccessPreflightToken','']) == '%1'}) then {_m setVariable ['ACME_chestAccessPreflightCancel',true,false];}; false",
            _token,
            netId _medic
        ];
        private _prepKeys = [];
        _prepKeys pushBack ([0x01, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
        _prepKeys pushBack ([0xF0, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
        _medic setVariable ["ACME_chestAccessPreflightKeyIDs", _prepKeys, false];

        [_patient, _medic, _leaseId, true, _nativeContinuousClass, _token] call ACME_fnc_chestAccessVestEvent;

        private _finishPrepUi = {
            params ["_m","_p","_tok"];
            if (isNull _m) exitWith {};
            {
                if (!(_x isEqualTo -1) && {!(_x isEqualTo "")}) then {[_x, "keydown"] call CBA_fnc_removeKeyHandler;};
            } forEach (_m getVariable ["ACME_chestAccessPreflightKeyIDs", []]);
            _m setVariable ["ACME_chestAccessPreflightKeyIDs", [], false];
            [false, _m, _p, _tok] call ACME_fnc_chestAccessPreparing;
        };

        private _abortPrep = {
            params ["_m","_p","_leaseId","_classKey","_tok","_finish",["_reopen",true]];
            if (isNull _m || {!local _m}) exitWith {};
            if ((_m getVariable ["ACME_chestAccessPreflightToken",""]) != _tok) exitWith {};
            if (_classKey == "checkbreathing") then {
                diag_log format ["[ACME CHECK BREATHING] preparation aborted; lease %1", _leaseId];
            };

            // Retire the provider theatre locally. Never wait for a casualty-owner packet to end this pose.
            [_m, _p, "stop", true, ((_m getVariable ["ACME_chestAccessProvider", []]) param [2, ""])] call ACME_fnc_chestAccessVestProvider;
            [_m,_p,_tok] call _finish;

            _m setVariable ["ACME_chestAccessPreflightActive", false, false];
            _m setVariable ["ACME_chestAccessPreflightToken", "", false];
            _m setVariable ["ACME_chestAccessPreflightCancel", false, false];

            private _cur = _m getVariable ["ACME_chestAccess_treatment", []];
            if ((_cur param [2,""]) == _leaseId) then {_m setVariable ["ACME_chestAccess_treatment", []];};
            if (!isNull _p) then {[_p,_m,_leaseId,false,_classKey] call ACME_fnc_chestAccessVestEvent;};

            // A canceled preparation never consumes Direct Pressure. It may visibly resume after its normal quiet window.
            if ((_m getVariable ["ACME_DP_PauseTreatmentClass",""]) == _classKey
                && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])}) then {
                _m setVariable ["ACME_DP_Paused", false, false];
                _m setVariable ["ACME_DP_PauseTreatmentClass", "", false];
                _m setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            };

            if (_reopen && {!isNull _p} && {alive _m} && {!(_m getVariable ["ACE_isUnconscious",false])}
                && {local _m} && {[_m] call ace_common_fnc_isPlayer}) then {
                ace_medical_gui_pendingReopen = false;
                ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
            };
        };

        private _launch = {
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_timedOut","_finish","_abort"];
            if (isNull _m || {!local _m}
                || {(_m getVariable ["ACME_chestAccessPreflightToken",""]) != _tok}) exitWith {};
            if (isNull _p) exitWith {
                [_m,_p,_leaseId,_classKey,_tok,_finish,false] call _abort;
            };

            private _cancelled = (_m getVariable ["ACME_chestAccessPreflightCancel", false])
                || {!alive _m}
                || {_m getVariable ["ACE_isUnconscious", false]}
                || {isNull objectParent _m && {([_m, _p] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}}
                || {objectParent _m isNotEqualTo objectParent _p};
            if (_cancelled) exitWith {
                [_m,_p,_leaseId,_classKey,_tok,_finish,true] call _abort;
            };

            // Preparation can last several seconds. Revalidate the ACTUAL treatment and interaction now, not the
            // cached menu result from the original click. A casualty/provider state or range change may never turn
            // into a delayed treatment start.
            private _stillTreatable = _args call ace_medical_treatment_fnc_canTreatCached;
            private _stillInteractive = [_m, _p, [["isNotInside","isNotSwimming","isNotInZeus"],["isNotSwimming","isNotInZeus"]] select (!isNull objectParent _m && {objectParent _m isEqualTo objectParent _p})] call ace_common_fnc_canInteractWith;
            if (!_stillTreatable || {!_stillInteractive} || {isNull objectParent _m && {([_m, _p] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}}
                || {objectParent _m isNotEqualTo objectParent _p}) exitWith {
                _m setVariable ["ACME_chestAccessPreflightCancel", true, false];
                [_m,_p,_leaseId,_classKey,_tok,_finish,true] call _abort;
            };

            private _heldBreathing = _classKey == "checkbreathing" && {isNull objectParent _m};
            private _pose = _m getVariable ["ACME_treatmentPoseState", []];
            private _provider = _m getVariable ["ACME_chestAccessProvider", []];
            if (_heldBreathing && {_timedOut
                || {(_pose param [1, ""]) != "chestAccess"}
                || {(_pose param [3, -1]) != 3}
                || {(_pose param [0, -2]) != (_provider param [1, -1])}
                || {(_provider param [0, objNull]) isNotEqualTo _p}}) exitWith {
                // A presentation failure must not consume the timer or leave a held provider behind.
                [_m,_p,_leaseId,_classKey,_tok,_finish,true] call _abort;
            };

            // CPR/BVM hand off synchronously. Check Breathing retains this exact held episode through its timer.
            if (!_heldBreathing) then {
                [_m, _p, "stop", true, ((_m getVariable ["ACME_chestAccessProvider", []]) param [2, ""])] call ACME_fnc_chestAccessVestProvider;
            };
            [_m,_p,_tok] call _finish;

            _m setVariable ["ACME_chestAccessPreflightActive", false, false];
            _m setVariable ["ACME_chestAccessPreflightToken", "", false];
            _m setVariable ["ACME_chestAccessPreflightCancel", false, false];

            if (_timedOut) then {
                diag_log format ["[ACME CHEST ACCESS] Prep timeout for %1 on %2; launching clinical action fail-open.",
                    _classKey, netId _p];
            };

            if (_heldBreathing) then {
                _m setVariable ["ACME_checkBreathingPose", [_p, _pose select 0, _leaseId], false];
                _m setVariable ["ACME_suppressNativeTreatmentAnim", true, false];
                diag_log format ["[ACME CHECK BREATHING] starting timer with provider held; lease %1", _leaseId];
            };
            private _started = _args call ACM_core_fnc_treatmentNative;
            if (_heldBreathing) then {_m setVariable ["ACME_suppressNativeTreatmentAnim", false, false];};
            if (!_started) then {
                if (_heldBreathing) then {
                    _m setVariable ["ACME_checkBreathingPose", [], false];
                    [_m, _p, "stop", false, _provider param [2, ""]] call ACME_fnc_chestAccessVestProvider;
                };
                private _cur = _m getVariable ["ACME_chestAccess_treatment", []];
                if ((_cur param [2,""]) == _leaseId) then {_m setVariable ["ACME_chestAccess_treatment", []];};
                [_p,_m,_leaseId,false,_classKey] call ACME_fnc_chestAccessVestEvent;

                if ((_m getVariable ["ACME_DP_PauseTreatmentClass",""]) == _classKey
                    && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])}) then {
                    _m setVariable ["ACME_DP_Paused", false, false];
                    _m setVariable ["ACME_DP_PauseTreatmentClass", "", false];
                    _m setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
                };

                if (alive _m && {!(_m getVariable ["ACE_isUnconscious",false])}
                    && {local _m} && {[_m] call ace_common_fnc_isPlayer}) then {
                    ace_medical_gui_pendingReopen = false;
                    ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
                };
            };
        };

        [{
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];
            if (isNull _m || {isNull _p} || {!local _m}
                || {(_m getVariable ["ACME_chestAccessPreflightToken",""]) != _tok}) exitWith {true};

            // Invalidation is terminal for this generation. Latch cancellation before reporting completion to
            // waitUntilAndExecute so stepping back into range cannot convert an invalidation frame into launch.
            private _invalid = (_m getVariable ["ACME_chestAccessPreflightCancel", false])
                || {!alive _m}
                || {_m getVariable ["ACE_isUnconscious", false]}
                || {isNull objectParent _m && {([_m, _p] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}}
                || {objectParent _m isNotEqualTo objectParent _p}
                || {!([_m, _p, [["isNotInside","isNotSwimming","isNotInZeus"],["isNotSwimming","isNotInZeus"]] select (!isNull objectParent _m && {objectParent _m isEqualTo objectParent _p})] call ace_common_fnc_canInteractWith)};
            if (_invalid) exitWith {
                _m setVariable ["ACME_chestAccessPreflightCancel", true, false];
                true
            };

            private _readyLease = _p getVariable ["ACME_chestAccess_readyLease", ""];
            private _ready = _p getVariable ["ACME_chestAccess_readyServer", -1];
            private _lease = _m getVariable ["ACME_chestAccess_treatment", []];
            private _patientReady = (_readyLease == (_lease param [2,""]))
                && {_ready isEqualType 0} && {_ready >= 0} && {serverTime >= _ready};
            if (!_patientReady) exitWith {false};
            if (_classKey != "checkbreathing" || {!isNull objectParent _m}) exitWith {true};

            private _provider = _m getVariable ["ACME_chestAccessProvider", []];
            private _pose = _m getVariable ["ACME_treatmentPoseState", []];
            private _matchingPose = (_provider param [0, objNull]) isEqualTo _p
                && {(_provider param [1, -1]) == (_pose param [0, -2])}
                && {(_pose param [1, ""]) == "chestAccess"};
            // No-carrier checks still enter the assessment hold, after any patient roll/lowering completes.
            if (!_matchingPose && {(_m getVariable ["ACME_checkBreathingProviderRequested", ""]) != _tok}) then {
                _m setVariable ["ACME_checkBreathingProviderRequested", _tok, false];
                [_m, _p, "start", false, _tok] call ACME_fnc_chestAccessVestProvider;
            };
            _matchingPose && {(_pose param [3, -1]) == 3}
        }, {
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];
            [_m,_p,_args,_tok,_leaseId,_classKey,false,_finish,_abort] call _launch;
        }, [_medic,_patient,_args,_token,_leaseId,_nativeContinuousClass,_launch,_finishPrepUi,_abortPrep], 12, {
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];
            [_m,_p,_args,_tok,_leaseId,_classKey,true,_finish,_abort] call _launch;
        }] call CBA_fnc_waitUntilAndExecute;
        true
    };

    // Auscultation owns its own modal display and provider pose. Base ACM launches the scope from the
    // treatment callback; do not put another asynchronous stance/weapon preflight in front of that callback.
    if (_nativeContinuousClass == "usestethoscope") exitWith {
        _this call ACM_core_fnc_treatmentNative
    };

    // Head tilt/chin lift is also only a launcher for a manual continuous hold. The generic preflight used to
    // recursively start the 0.001 s treatment and then re-arm medical-menu reopen, which immediately killed the
    // newly-created hold unless the provider happened to already be in a ready crouched state.
    if (_nativeContinuousClass == "beginheadtiltchinlift") exitWith {
        // A provider supporting manual Semi-Fowler already has both hands occupied. Reject
        // before native callbacks, recovery cancellation or posture events can mutate the patient.
        if (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]) exitWith {
            ["Finish the current hands-on maneuver before head tilt/chin lift.", 2, _medic]
                call ace_common_fnc_displayTextStructured;
            false
        };
        _this call ACM_core_fnc_treatmentNative
    };

    if (_nativeContinuousClass in ["usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"]) exitWith {
        // Match CPR: BVM takes provider/clinical priority without destroying persistent Direct Pressure.
        // This path covers already-prepared/no-carrier cases where the chest-access preflight above did not run.
        if (_dpSamePatient) then {[_medic, _nativeContinuousClass] call _fnc_dpPauseForManeuver;};
        private _startedContinuous = _this call ACM_core_fnc_treatmentNative;
        if (!_startedContinuous && {_dpSamePatient}
            && {(_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == _nativeContinuousClass}) then {
            _medic setVariable ["ACME_DP_Paused", false, false];
            _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
            _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
        };
        _startedContinuous
    };

    // Preserve the existing Direct Pressure handoff for CPR.
    if (_nativeContinuousClass == "cpr") exitWith {
        if (_dpSamePatient) then {[_medic, _nativeContinuousClass] call _fnc_dpPauseForManeuver;};
        private _startedContinuous = _this call ACM_core_fnc_treatmentNative;
        if (!_startedContinuous && {_dpSamePatient} && {(_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == _nativeContinuousClass}) then {
            _medic setVariable ["ACME_DP_Paused", false, false];
            _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        };
        _startedContinuous
    };

    // Resolve ACME's provider-theatre policy BEFORE native treatment starts. When one of these modes is selected,
    // fn_treatmentNative is told not to enqueue ACM/ACE's generic medic animation. Previously the native bandage
    // motion was already in the animation queue by the time ACME started the requested chest/head/NCD gesture, so
    // it won later and made the specific animation appear to never play.
    private _cfg = configFile >> "ace_medical_treatment_actions" >> _classname;
    private _category = toLowerANSI getText (_cfg >> "category");
    private _part = toLowerANSI _bodyPart;
    private _classKey = toLowerANSI _classname;
    private _torso = _part in ["body", "torso", "chest", "abdomen"];
    private _mode = "";
    private _exactAnim = "";
    private _gestureWindow = 2.4;

    if ((_classKey find "performncd") >= 0 || {(_classKey find "narspear") >= 0}) then {
        _mode = "ncdSeat";
        _gestureWindow = 5.0;
    } else {
        if ((_classKey find "checkbreathing") >= 0) then {
            _exactAnim = "AinvPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_medic";
        } else {
            if (_torso && {(_classKey find "pressurebandage") >= 0}) then {
                _exactAnim = "AinvPknlMstpSnonWnonDnon_medic3";
            } else {
                if (_torso && {(_classKey find "emergencytraumadressing") >= 0}) then {
                    _exactAnim = "AinvPknlMstpSnonWnonDnon_medic4";
                } else {
                    if (_category == "bandage" && {_torso}) then {
                        _mode = "torsoBandage";
                    } else {
                        if (_category == "bandage" && {_part == "head"}) then {
                            private _relative = _patient worldToModel (getPosWorld _medic);
                            _mode = ["headBandageLeft", "headBandageRight"] select ((_relative param [0, 0]) > 0);
                        };
                    };
                };
            };
        };
    };
    private _ownsProviderAnim = (_mode != "") || {_exactAnim != ""};

    // B177 button-responsiveness invariant: provider presentation NEVER gates clinical treatment start.
    // Earlier builds waited for weapon holster + crouch before calling fnc_treatmentNative, producing a dead
    // 0.5-3.0 second interval after a valid button click. Native treatment/progress now starts on this frame.
    // ACME-owned provider theatre catches up independently after the click and may never become a clinical mutex.
    private _headOwned = _classname in ["ACME_ElevateHead", "ACME_LowerHead"];

    // Recovery-position changes, head positioning and any treatment that must roll a casualty out of recovery are
    // incompatible with physically maintaining wound pressure. Pause the clinical marker only for that maneuver.
    private _dpPatientManeuver = _classKey in ["recoveryposition", "cancelrecoveryposition", "acme_elevatehead", "acme_lowerhead"]
        || {(getNumber (_cfg >> "ACM_rollToBack")) > 0}
        || {(_patient getVariable ["ACM_airway_RecoveryPosition_State", false]) && {(getNumber (_cfg >> "ACM_cancelRecovery")) > 0}};
    if (_dpSamePatient && {_dpPatientManeuver}) then {[_medic, _classKey] call _fnc_dpPauseForManeuver;};

    // Retire any pre-B177 deferred presentation generation immediately. Its token change makes already-queued
    // callbacks inert, so a hot-loaded client cannot launch an old delayed treatment after this click.
    if (local _medic) then {
        _medic setVariable ["ACME_treatmentPreflightActive", false, false];
        _medic setVariable ["ACME_treatmentPreflightToken", "", false];
        _medic setVariable ["ACME_treatmentPreflightBypass", [], false];
        _medic setVariable ["ACME_treatmentPreflightStartedAt", -1, false];

        // Presentation begins now but never delays native progress. ACME-owned poses stop the menu pose and issue
        // the one holster request immediately; their pose controller waits for visual readiness independently.
        if (_ownsProviderAnim) then {
            [_medic, true] call ACME_fnc_menuPoseStop;
            if (currentWeapon _medic != "") then {[_medic] call ACME_fnc_medicAnimationPrep;};
        };
    };

    // A newly accepted head-position action replaces the previous finite treatment's exit lease.
    // Its leftover rate record must not make the Putdown controller mistake its own startup for a takeover.
    if (_headOwned && {local _medic}) then {
        // B182: replacing a native animation-rate lease is a real speed handoff. Retire the old lease/pose first,
        // then restore 1.0 unless the incoming/current controller has already acquired explicit speed ownership.
        _medic setVariable ["ACME_nativeTreatmentRate", [], true];
        [_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
        [_medic, true] call ACME_fnc_menuPoseStop;
        if !([_medic] call ACME_fnc_providerAnimSpeedOwned) then {
            _medic setAnimSpeedCoef 1;
            ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
        };
    };

    // Head positioning is head-selection only. Pass the selected body part through unchanged.
    private _nativeArgs = +_this;

    // Retire only the visual DP loop before native/ACME treatment animation is queued.  Ordinary treatments keep
    // the synchronized pressure marker active; true maneuvers above set ACME_DP_Paused so the shared tick clears it.
    if (_dpSamePatient && {local _medic}) then {
        _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
        _medic setVariable ["ACME_DP_InPose", false, false];
        _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
        _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
    };

    if (_dpSamePatient && {local _medic}) then {
        // From this point until ACE emits treatment success/failure, Direct Pressure is animation-passive.
        _medic setVariable ["ACME_DP_TreatmentBusy", true, false];
    };
    if ((_ownsProviderAnim || {_headOwned}) && {local _medic}) then {
        _medic setVariable ["ACME_suppressNativeTreatmentAnim", true, false];
    };
        // Ordinary ACE work has no treatmentPose controller of its own. Its existing completion events
        // retire this animation-only rate without changing native treatment/progress-bar duration.
    private _nativeRateRecord = [];
    if (_mode == "" && {!_headOwned} && {local _medic} && {isNull objectParent _medic}) then {
            [_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
            [_medic, true] call ACME_fnc_menuPoseStop;
            private _serial = (_medic getVariable ["ACME_nativeTreatmentRateSerial", 0]) + 1;
            _medic setVariable ["ACME_nativeTreatmentRateSerial", _serial, false];
            _nativeRateRecord = [_serial, _patient, _bodyPart, _classname, _medic getVariable ["ACME_treatmentPoseEpoch", -1]];
            _medic setVariable ["ACME_nativeTreatmentRate", _nativeRateRecord, true];
            private _rate = call ACME_fnc_choreographyRate;
            _medic setAnimSpeedCoef _rate;
            ["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;
        };

    private _started = _nativeArgs call ACM_core_fnc_treatmentNative;
    if (local _medic) then {
        _medic setVariable ["ACME_suppressNativeTreatmentAnim", false, false];
    };
    if (!_started && {_dpSamePatient}) then {
        _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
        if ((_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == _classKey) then {
            _medic setVariable ["ACME_DP_Paused", false, false];
            _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        };
    };

    if (!_started && {_nativeRateRecord isNotEqualTo []}
        && {(_medic getVariable ["ACME_nativeTreatmentRate", []]) isEqualTo _nativeRateRecord}) then {
        _medic setVariable ["ACME_nativeTreatmentRate", [], true];
    };
    if (!_started && {local _medic} && {!([_medic] call ACME_fnc_providerStanceOwned)}) then {
        _medic setAnimSpeedCoef 1;
        ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
    };

    if (_started && {local _medic} && {!isNull _medic} && {isNull objectParent _medic}) then {
        if (_mode != "") then {
            [{
                params ["_m", "_mode", "_window", "_patient"];
                if (!isNull _m && {alive _m} && {local _m}) then {
                    [_m, _mode, _window, _patient] call ACME_fnc_treatmentGesture;
                };
            }, [_medic, _mode, _gestureWindow, _patient]] call CBA_fnc_execNextFrame;
        } else {
            if (_exactAnim != "") then {
                [{
                    params ["_m", "_anim"];
                    if (!isNull _m && {alive _m} && {local _m}) then {
                        [_m, _anim, 1] call ACME_fnc_doAnim;
                    };
                }, [_medic, _exactAnim]] call CBA_fnc_execNextFrame;
            };
        };
    };
    _started
};

// Ventilator connector: inventory/state is committed only after its own acknowledgement path accepts the action.
if (!local _medic || {isNull _medic} || {isNull _patient}) exitWith {false};
if (uiNamespace getVariable ["ace_interact_menu_cursorMenuOpened", false]) exitWith {
    [ace_medical_treatment_fnc_treatment, _this] call CBA_fnc_execNextFrame;
    true
};
if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
if !([_medic, _patient, _interactionChecks] call ace_common_fnc_canInteractWith) exitWith {false};
if !([_medic, _patient] call ACME_fnc_ventRecoveryNear) exitWith {false};
[_medic, _patient] call ACME_fnc_ventConnectPatient;
true
