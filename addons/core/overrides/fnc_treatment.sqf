#include "..\script_component.hpp"
/* ACM Extended treatment bridge.
 * ACME owns only provider preflight, requested intervention-specific gestures, and the ventilator connector.
 * Native ACM/ACE remains authoritative for treatment timing, inventory, callbacks, cancellation and patient state.
 */
params ["_medic", "_patient", "_bodyPart", "_classname"];

// This debug command has no physical treatment or provider animation. Execute directly,
// so empty-hands preflight, the progress bar and the generic patient settle cannot consume the click.
if (_classname == "ACME_DebugInduceSeizure") exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !((toLowerANSI _bodyPart) == "head" && {[] call ACME_fnc_debugEnabled}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreat) exitWith {false};
    [_patient, "debugSeizure", [_medic, _patient]] call ACME_fnc_ownerDispatch;
    true
};

// Direct Pressure is an immediate medical-menu state toggle, not an ACE timed treatment. Running it through the
// normal treatment pipeline closes the medical menu for the progress dialog and invokes the generic weapon/stance
// preflight before callbackSuccess. Apply/Stop therefore execute here and repaint the existing menu in place.
private _fnc_refreshDirectPressureMenu = {
    params ["_m", "_p"];
    if (!hasInterface || {isNil "ACE_player"} || {_m isNotEqualTo ACE_player}) exitWith {};
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

    // Preserve the existing hands-on-wound one-shot, but do not create a progress bar or treatment animation.
    [_patient, 0.85] call ACME_fnc_markImportantSfx;
    [_medic, "ACME_DirectPressure"] remoteExec ["say3D", 0];

    [_medic, _patient, _bodyPart] call ACME_fnc_directPressureStart;
    [_medic, _patient] call _fnc_refreshDirectPressureMenu;
    _medic getVariable ["ACME_DP_Active", false]
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

// Opening a shared workspace must not wait for a free kneeling/holster animation.
// Each actual intervention inside the panel retains its own checks and animation.
if (_classname in ["ACME_ApplyChestSeal", "ACME_PerformNARSPEAR", "ACME_VentOpenPatient"]) exitWith {
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
    if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
    if !([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith) exitWith {false};
    if ((_medic distance _patient) > ace_medical_gui_maxDistance) exitWith {false};
    ace_medical_gui_pendingReopen = false;
    if (_classname == "ACME_VentOpenPatient") then {
        [_patient] call ACME_fnc_ventPanelOpen;
    } else {
        [_medic, _patient, _bodyPart, ["seal", "spear"] select (_classname == "ACME_PerformNARSPEAR")] call ACME_fnc_chestSealOpen;
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
    private _needsFrontNormalize = alive _patient
        && {isNull objectParent _patient}
        && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll}
        && {_actualChestSide == "back"};
    private _needsPhysicalPrep = _needsFrontNormalize
        || {((vest _patient) != "" && {(count _chestSaved) != 2})}
        || {_patient getVariable ["ACME_headElevated", false]
            && {!(_patient getVariable ["ACME_headElev_Suspended", false])}};

    if (_needsChestAccess && {_needsPhysicalPrep} && {!_alreadyPrepared}
        && {local _medic} && {!isNull _medic} && {alive _medic}) exitWith {
        if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
        if !([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith) exitWith {false};
        if ((_medic distance _patient) > ace_medical_gui_maxDistance) exitWith {false};
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
        _medic setVariable ["ACME_chestAccess_treatment", [_patient, _nativeContinuousClass, _leaseId]];

        // The medical menu closes on the accepted click. Its normal pending-reopen handler is suppressed by the
        // renderer while this flag is active; only an explicit abort/failure reopens it.
        ace_medical_gui_pendingReopen = false;
        if (dialog) then {closeDialog 0;};
        [true, _medic, _patient, _token] call ACME_fnc_chestAccessPreparing;

        // Escape and F0 cancel preparation, not the next intervention. Handler IDs are generation-local strings.
        private _cancelCode = compile format [
            "private _m=ACE_player; if (!isNull _m && {(_m getVariable ['ACME_chestAccessPreflightToken','']) == '%1'}) then {_m setVariable ['ACME_chestAccessPreflightCancel',true,false];}; false",
            _token
        ];
        private _prepKeys = [];
        _prepKeys pushBack ([0x01, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
        _prepKeys pushBack ([0xF0, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
        _medic setVariable ["ACME_chestAccessPreflightKeyIDs", _prepKeys, false];

        [_patient, _medic, _leaseId, true, _nativeContinuousClass] call ACME_fnc_chestAccessVestEvent;

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

            // Retire the provider theatre locally. Never wait for a casualty-owner packet to end this pose.
            [_m, _p, "stop", true, _tok] call ACME_fnc_chestAccessVestProvider;
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
                && {_m isEqualTo ACE_player}) then {
                ace_medical_gui_pendingReopen = false;
                ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
            };
        };

        private _launch = {
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_timedOut","_finish","_abort"];
            if (isNull _m || {isNull _p} || {!local _m}
                || {(_m getVariable ["ACME_chestAccessPreflightToken",""]) != _tok}) exitWith {};

            private _cancelled = (_m getVariable ["ACME_chestAccessPreflightCancel", false])
                || {!alive _m}
                || {_m getVariable ["ACE_isUnconscious", false]}
                || {(_m distance _p) > ace_medical_gui_maxDistance}
                || {objectParent _m isNotEqualTo objectParent _p};
            if (_cancelled) exitWith {
                [_m,_p,_leaseId,_classKey,_tok,_finish,true] call _abort;
            };

            // Critical ownership boundary: retire medic4 synchronously on the provider machine BEFORE native CPR/BVM
            // or another queued treatment acquires animation. This removes the dedicated-server late-stop race.
            [_m, _p, "stop", true, _tok] call ACME_fnc_chestAccessVestProvider;
            [_m,_p,_tok] call _finish;

            _m setVariable ["ACME_chestAccessPreflightActive", false, false];
            _m setVariable ["ACME_chestAccessPreflightToken", "", false];
            _m setVariable ["ACME_chestAccessPreflightCancel", false, false];

            if (_timedOut) then {
                diag_log format ["[ACME CHEST ACCESS] Prep timeout for %1 on %2; launching clinical action fail-open.",
                    _classKey, netId _p];
            };

            private _started = _args call ACM_core_fnc_treatmentNative;
            if (!_started) then {
                private _cur = _m getVariable ["ACME_chestAccess_treatment", []];
                if ((_cur param [2,""]) == _leaseId) then {_m setVariable ["ACME_chestAccess_treatment", []];};
                [_p,_m,_leaseId,false,_classKey] call ACME_fnc_chestAccessVestEvent;

                if ((_m getVariable ["ACME_DP_PauseTreatmentClass",""]) == _classKey
                    && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])}) then {
                    _m setVariable ["ACME_DP_Paused", false, false];
                    _m setVariable ["ACME_DP_PauseTreatmentClass", "", false];
                    _m setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
                };

                if (alive _m && {!(_m getVariable ["ACE_isUnconscious",false])} && {_m isEqualTo ACE_player}) then {
                    ace_medical_gui_pendingReopen = false;
                    ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
                };
            };
        };

        [{
            params ["_m","_p","_args","_tok","_leaseId","_classKey","_launch","_finish","_abort"];
            if (isNull _m || {isNull _p} || {!local _m}
                || {(_m getVariable ["ACME_chestAccessPreflightToken",""]) != _tok}
                || {_m getVariable ["ACME_chestAccessPreflightCancel", false]}
                || {!alive _m}
                || {_m getVariable ["ACE_isUnconscious", false]}
                || {(_m distance _p) > ace_medical_gui_maxDistance}
                || {objectParent _m isNotEqualTo objectParent _p}) exitWith {true};

            private _readyLease = _p getVariable ["ACME_chestAccess_readyLease", ""];
            private _ready = _p getVariable ["ACME_chestAccess_readyServer", -1];
            private _lease = _m getVariable ["ACME_chestAccess_treatment", []];
            (_readyLease == (_lease param [2,""]))
                && {_ready isEqualType 0}
                && {_ready >= 0}
                && {serverTime >= _ready}
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
        _this call ACM_core_fnc_treatmentNative
    };

    if (_nativeContinuousClass in ["usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"]) exitWith {
        _this call ACM_core_fnc_treatmentNative
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

    // One empty-hands request and one transition to crouch before native treatment starts.
    private _bypass = _medic getVariable ["ACME_treatmentPreflightBypass", []];
    private _isBypass = (_bypass isEqualType []) && {count _bypass >= 3}
        && {(_bypass select 0) isEqualTo _patient}
        && {(_bypass select 1) == _bodyPart}
        && {(_bypass select 2) == _classname};
    private _headOwned = _classname in ["ACME_ElevateHead", "ACME_LowerHead"];

    // Recovery-position changes, head positioning and any treatment that must roll a casualty out of recovery are
    // incompatible with physically maintaining wound pressure.  Pause the clinical marker only for that maneuver.
    private _dpPatientManeuver = _classKey in ["recoveryposition", "cancelrecoveryposition", "acme_elevatehead", "acme_lowerhead"]
        || {(getNumber (_cfg >> "ACM_rollToBack")) > 0}
        || {(_patient getVariable ["ACM_airway_RecoveryPosition_State", false]) && {(getNumber (_cfg >> "ACM_cancelRecovery")) > 0}};
    if (_dpSamePatient && {_dpPatientManeuver}) then {[_medic, _classKey] call _fnc_dpPauseForManeuver;};

    // Fast path: only a genuinely empty-handed crouch may bypass preflight. Both the logical weapon selection
    // and the visible Wnon/Snon skeleton must agree; sidearms can clear one before the other.
    private _animNow = if (!isNull _medic) then {toLowerANSI animationState _medic} else {""};
    private _visuallyEmptyNow = !isNull _medic
        && {((_animNow find "wnon") >= 0)}
        && {((_animNow find "snon") >= 0)};
    private _emptyHandsNow = !isNull _medic
        && {(currentWeapon _medic == "")}
        && {_visuallyEmptyNow};

    // A visible Direct Pressure hold is already an authored empty-hands provider theatre. It remains the only
    // special case because that hold itself disables ordinary weapon transitions.
    private _dpPoseReady = _dpSamePatient && {
        (_medic getVariable ["ACME_DP_InPose", false]) || {_animNow == "acme_directpressurehold"}
    };
    private _preflightReady = _dpPoseReady || {_emptyHandsNow && {stance _medic == "CROUCH"}};

    if (!_isBypass && {!_headOwned} && {!_preflightReady} && {local _medic} && {!isNull _medic} && {alive _medic} && {isNull objectParent _medic}) exitWith {
        if (_medic getVariable ["ACME_treatmentPreflightActive", false]) exitWith {false};

        _medic setVariable ["ACME_treatmentPreflightActive", true, false];
        private _args = +_this;
        private _token = format ["%1:%2:%3", clientOwner, netId _medic, diag_tickTime];
        _medic setVariable ["ACME_treatmentPreflightToken", _token, false];

        // Phase 1: issue exactly one holster request and wait until the handgun/long gun is both logically gone
        // and visually in Wnon/Snon. Do not start a stance transition while the weapon-away RTM still owns the arms.
        [_medic] call ACME_fnc_medicAnimationPrep;
        [{
            params ["_m", "_args", "_tok"];
            if (isNull _m || {!alive _m} || {!local _m}
                || {(_m getVariable ["ACME_treatmentPreflightToken", ""]) != _tok}) exitWith {true};
            private _anim = toLowerANSI animationState _m;
            (currentWeapon _m == "")
                && {((_anim find "wnon") >= 0)}
                && {((_anim find "snon") >= 0)}
        }, {
            params ["_m", "_args", "_tok"];
            if (isNull _m || {!alive _m} || {!local _m}
                || {(_m getVariable ["ACME_treatmentPreflightToken", ""]) != _tok}) exitWith {
                if (!isNull _m && {local _m} && {(_m getVariable ["ACME_treatmentPreflightToken", ""]) == _tok}) then {
                    _m setVariable ["ACME_treatmentPreflightActive", false, false];
                    _m setVariable ["ACME_treatmentPreflightToken", "", false];
                    _m setUnitPos "AUTO";
                };
            };

            // Phase 2: only after empty hands are visually settled do we move the provider into the treatment crouch.
            _m setUnitPos "MIDDLE";
            private _transition = switch (stance _m) do {
                case "STAND": {"AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
                case "PRONE": {"AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
                default {""};
            };
            if (_transition != "") then {[_m, _transition, 1] call ACME_fnc_doAnim;};

            [{
                params ["_u", "_callArgs", "_token"];
                if (isNull _u || {!alive _u} || {!local _u}
                    || {(_u getVariable ["ACME_treatmentPreflightToken", ""]) != _token}) exitWith {true};
                private _anim2 = toLowerANSI animationState _u;
                (currentWeapon _u == "")
                    && {((_anim2 find "wnon") >= 0)}
                    && {((_anim2 find "snon") >= 0)}
                    && {stance _u == "CROUCH"}
            }, {
                params ["_u", "_callArgs", "_token"];
                if (isNull _u || {!alive _u} || {!local _u}
                    || {(_u getVariable ["ACME_treatmentPreflightToken", ""]) != _token}) exitWith {
                    if (!isNull _u && {local _u} && {(_u getVariable ["ACME_treatmentPreflightToken", ""]) == _token}) then {
                        _u setVariable ["ACME_treatmentPreflightActive", false, false];
                        _u setVariable ["ACME_treatmentPreflightToken", "", false];
                        _u setUnitPos "AUTO";
                    };
                };

                _u setVariable ["ACME_treatmentPreflightActive", false, false];
                _u setVariable ["ACME_treatmentPreflightBypass", [_callArgs select 1, _callArgs select 2, _callArgs select 3], false];
                _callArgs call ace_medical_treatment_fnc_treatment;
                // This recursive call starts the progress dialog after the original ButtonClick event has already
                // finished. Mirror ACE's native event order by arming reopen AFTER progressBar closes the medical menu.
                if (hasInterface && {!isNil "ACE_player"} && {_u isEqualTo ACE_player}) then {
                    ace_medical_gui_pendingReopen = true;
                };
                _u setVariable ["ACME_treatmentPreflightBypass", [], false];
                _u setVariable ["ACME_treatmentPreflightToken", "", false];
            }, [_m, _args, _tok], 1.8, {
                params ["_u", "_callArgs", "_token"];
                if (isNull _u || {!local _u} || {(_u getVariable ["ACME_treatmentPreflightToken", ""]) != _token}) exitWith {};
                _u setVariable ["ACME_treatmentPreflightActive", false, false];
                _u setVariable ["ACME_treatmentPreflightBypass", [], false];
                _u setVariable ["ACME_treatmentPreflightToken", "", false];
                _u setUnitPos "AUTO";
            }] call CBA_fnc_waitUntilAndExecute;
        }, [_medic, _args, _token], 3.0, {
            params ["_m", "_args", "_tok"];
            if (isNull _m || {!local _m} || {(_m getVariable ["ACME_treatmentPreflightToken", ""]) != _tok}) exitWith {};
            _m setVariable ["ACME_treatmentPreflightActive", false, false];
            _m setVariable ["ACME_treatmentPreflightBypass", [], false];
            _m setVariable ["ACME_treatmentPreflightToken", "", false];
            _m setUnitPos "AUTO";
        }] call CBA_fnc_waitUntilAndExecute;
        true
    };

    if (_isBypass) then {
        _medic setVariable ["ACME_treatmentPreflightActive", false, false];
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
    if (_ownsProviderAnim && {local _medic}) then {
        _medic setVariable ["ACME_suppressNativeTreatmentAnim", true, false];
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

    if (_started && {local _medic} && {!isNull _medic} && {isNull objectParent _medic}) then {
        if (_mode != "") then {
            [{
                params ["_m", "_mode", "_window"];
                if (!isNull _m && {alive _m} && {local _m}) then {
                    [_m, _mode, _window] call ACME_fnc_treatmentGesture;
                };
            }, [_medic, _mode, _gestureWindow]] call CBA_fnc_execNextFrame;
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
if !(_this call ace_medical_treatment_fnc_canTreat) exitWith {false};
if !([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith) exitWith {false};
if !([_medic, _patient] call ACME_fnc_ventRecoveryNear) exitWith {false};
[_medic, _patient] call ACME_fnc_ventConnectPatient;
true
