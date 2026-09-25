/* Active provider-supported Semi-Fowler for casualties with neither backpack nor plate carrier.
 *
 * The casualty still uses the normal ACME_HeadElevPatientGrab -> Hold animation. The provider uses the authored
 * Putdown family that normally returns a casualty to supine:
 *   crouch -> ..._Putdown -> frozen Putdown end pose while support is maintained
 *   release -> Putdown_...crouch -> normal movable crouch
 *
 * This is a real continuous maneuver: Escape/F0, distance/vehicle loss, provider invalidation, movement or a
 * competing flattening intervention releases the hold and lays the casualty back down.
 */
params ["_medic", "_patient", "_bodyPart", "_token", ["_ready", false]];
if (!local _medic) exitWith {[_medic, "headElevHoldStart", _this] call ACME_fnc_ownerDispatch;};

private _releasePatient = {
    [_patient, "headElevHoldRelease", [_medic, _patient, _token]] call ACME_fnc_ownerDispatch;
};

if (!hasInterface || {!isPlayer _medic} || {_medic != ACE_player} || {!alive _medic} || {isNull _patient}
    || {!alive _patient} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}) exitWith {call _releasePatient;};

if (!_ready) exitWith {
    // Let the treatment that created the posture close its own dialog first. This generation remains bound to the
    // exact patient pose token; a canceled/replaced placement can never wake this callback later.
    ace_medical_gui_pendingReopen = false;
    private _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
    if (!isNull _menu) then {_menu closeDisplay 1;};
    [{
        params ["_medic", "_patient", "_bodyPart", "_token"];
        !dialog
            && {(_patient getVariable ["ACME_headElev_poseToken", ""]) == _token}
            && {_patient getVariable ["ACME_headElevated", false]}
    }, {
        (_this + [true]) call ACME_fnc_headElevHoldStart;
    }, [_medic, _patient, _bodyPart, _token], 3, {
        params ["_medic", "_patient", "_bodyPart", "_token"];
        [_patient, "headElevHoldRelease", [_medic, _patient, _token]] call ACME_fnc_ownerDispatch;
    }] call CBA_fnc_waitUntilAndExecute;
};

if ((_patient getVariable ["ACME_headElev_poseToken", ""]) != _token
    || {!(_patient getVariable ["ACME_headElevated", false])}
    || {_patient getVariable ["ACME_headElev_Suspended", false]}) exitWith {call _releasePatient;};

private _hold = _patient getVariable ["ACME_headElev_hold", []];
if ((_hold param [0,objNull,[objNull]]) isNotEqualTo _medic
    || {(_hold param [1,"",[""]]) != _token}) exitWith {call _releasePatient;};

[[ _medic, _patient, _bodyPart, [_token] ], {
    params ["_medic", "_patient", "_bodyPart", "_extra"];
    private _token = _extra select 0;

    _medic setVariable ["ACME_headElev_holding", [_patient, _token], true];
    // Match CPR/BVM's mouse-cancel behavior. Bind the handler to this exact continuous-action generation so a
    // stale F0 callback is harmless even if CBA delivers it after another maneuver has taken ownership.
    private _oldCancelID = _medic getVariable ["ACME_headElev_manualCancelID", -1];
    if (!(_oldCancelID isEqualTo -1) && {!(_oldCancelID isEqualTo "")}) then {
        [_oldCancelID, "keydown"] call CBA_fnc_removeKeyHandler;
    };
    private _continuousEpoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
    private _cancelCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch',-2]) == %1) then {missionNamespace setVariable ['ACM_core_ContinuousAction_Active',false];}; false",
        _continuousEpoch
    ];
    private _cancelID = [0xF0, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
    _medic setVariable ["ACME_headElev_manualCancelID", _cancelID, false];

    // Retire only an older manual-hold presentation owned by this provider.
    private _oldPFH = _medic getVariable ["ACME_headElev_manualAnimPFH", -1];
    if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

    private _animSerial = (_medic getVariable ["ACME_headElev_manualAnimSerial", 0]) + 1;
    _medic setVariable ["ACME_headElev_manualAnimSerial", _animSerial, false];
    private _animToken = format ["manual-sf:%1:%2:%3", clientOwner, _animSerial, _token];
    _medic setVariable ["ACME_headElev_manualAnimToken", _animToken, false];

    private _entry = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
    private _holdState = "AinvPknlMstpSnonWnonDnon_Putdown";
    private _entryLC = toLowerANSI _entry;
    private _holdLC = toLowerANSI _holdState;

    // Manual support uses the same episode receiver as every other frozen provider pose.
    [_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
    private _poseEpoch = (_medic getVariable ["ACME_treatmentPoseEpoch", 0]) + 1;
    _medic setVariable ["ACME_treatmentPoseEpoch", _poseEpoch, true];
    _medic setVariable ["ACME_treatmentPoseEpisode", [_poseEpoch, true], true];
    _medic setVariable ["ACME_headElev_manualPoseEpoch", _poseEpoch, false];
    private _rate = call ACME_fnc_choreographyRate;
    _medic setAnimSpeedCoef _rate;
    private _jip = format ["ACME_treatmentPose_%1_%2", netId _medic, _poseEpoch];
    ["ACME_treatmentPoseSync", [_medic, _poseEpoch, "run", "", -1, clientOwner, _rate], _jip] call CBA_fnc_globalEventJIP;
    [_jip, _medic] call CBA_fnc_removeGlobalEventJIP;

    private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep;
    if !(_prepDelay isEqualType 0) then {_prepDelay = 0;};
    private _prepUntil = CBA_missionTime + ((_prepDelay max 0) max 0.05);

    private _pfh = [{
        params ["_args","_handle"];
        _args params ["_m","_p","_poseToken","_animToken","_entry","_entryLC","_holdState","_holdLC","_prepUntil","_stage","_stageAt","_lastAssert","_poseEpoch"];

        if (isNull _m || {!local _m}
            || {(_m getVariable ["ACME_headElev_manualAnimToken",""]) != _animToken}
            || {!((_m getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_poseEpoch, true])}
            || {!alive _m}
            || {_m getVariable ["ACE_isUnconscious",false]}
            || {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active",false])}) exitWith {
            [_handle] call CBA_fnc_removePerFrameHandler;
            if (!isNull _m && {local _m} && {(_m getVariable ["ACME_headElev_manualAnimToken",""]) == _animToken}) then {
                _m setVariable ["ACME_headElev_manualAnimPFH",-1,false];
                private _cancelID = _m getVariable ["ACME_headElev_manualCancelID",-1];
                if (!(_cancelID isEqualTo -1) && {!(_cancelID isEqualTo "")}) then {
                    [_cancelID, "keydown"] call CBA_fnc_removeKeyHandler;
                };
                _m setVariable ["ACME_headElev_manualCancelID",-1,false];
            };
        };

        private _now = CBA_missionTime;
        private _state = toLowerANSI animationState _m;

        if (_stage == -1) exitWith {
            private _empty = currentWeapon _m == "" && {(_state find "wnon") >= 0} && {(_state find "snon") >= 0};
            if (!_empty && {_now < _prepUntil}) exitWith {};
            if (currentWeapon _m != "") then {_m selectWeapon "";};
            _m setUnitPos "MIDDLE";
            [_m, _entry, 2] call ACME_fnc_doAnim;
            _args set [9,0];
            _args set [10,_now];
        };

        if (_stage == 0) exitWith {
            // Patient lift already started with the Semi-Fowler episode. Manual provider support owns only the
            // provider entry/hold/exit and never gates or replays the patient animation.
            // The transition normally lands in the static Putdown state. If another move graph masks that target,
            // force the authored end state once after a bounded entry window instead of replaying the transition.
            if (_state == _holdLC) then {
                _m setAnimSpeedCoef 0;
                private _jip = format ["ACME_treatmentPose_%1_%2", netId _m, _poseEpoch];
                ["ACME_treatmentPoseSync", [_m, _poseEpoch, "hold", _holdState, 0, clientOwner], _jip] call CBA_fnc_globalEventJIP;
                [_jip, _m] call CBA_fnc_removeGlobalEventJIP;
                _args set [9,1];
                _args set [10,_now];
                _args set [11,_now];
            } else {
                if (_now - _stageAt > 2.75) then {
                    [_m, _holdState, 2] call ACME_fnc_doAnim;
                    _args set [10,_now];
                };
            };
        };

        if (_stage == 1) then {
            // This held frame has provider-animation priority while the continuous maneuver is valid. Reassert only
            // on real state/speed drift; flattening interventions cancel the maneuver through the clinical PFH below.
            private _stateDrift = _state != _holdLC;
            private _speedDrift = getAnimSpeedCoef _m != 0;
            if (_stateDrift || {_speedDrift}) then {
                if (_stateDrift) then {[_m, _holdState, 2] call ACME_fnc_doAnim;};
                _m setAnimSpeedCoef 0;
                _args set [11,_now];
            };
        };
    }, 0, [_medic,_patient,_token,_animToken,_entry,_entryLC,_holdState,_holdLC,_prepUntil,-1,CBA_missionTime,-1,_poseEpoch]] call CBA_fnc_addPerFrameHandler;
    _medic setVariable ["ACME_headElev_manualAnimPFH", _pfh, false];
}, {
    params ["_medic", "_patient", "_bodyPart", "_extra"];
    private _token = _extra select 0;

    if ((_medic getVariable ["ACME_headElev_holding", []]) isEqualTo [_patient, _token]) then {
        _medic setVariable ["ACME_headElev_holding", [], true];
    };

    private _pfh = _medic getVariable ["ACME_headElev_manualAnimPFH", -1];
    if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    _medic setVariable ["ACME_headElev_manualAnimPFH", -1, false];

    private _cancelID = _medic getVariable ["ACME_headElev_manualCancelID",-1];
    if (!(_cancelID isEqualTo -1) && {!(_cancelID isEqualTo "")}) then {
        [_cancelID, "keydown"] call CBA_fnc_removeKeyHandler;
    };
    _medic setVariable ["ACME_headElev_manualCancelID",-1,false];

    private _animToken = _medic getVariable ["ACME_headElev_manualAnimToken", ""];
    _medic setVariable ["ACME_headElev_manualAnimToken", "", false];

    private _poseEpoch = _medic getVariable ["ACME_headElev_manualPoseEpoch", -1];
    _medic setVariable ["ACME_headElev_manualPoseEpoch", -1, false];
    private _ownsPose = local _medic && {(_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_poseEpoch, true]};
    if (_ownsPose) then {
        _medic setVariable ["ACME_treatmentPoseEpisode", [_poseEpoch, false], true];
        [format ["ACME_treatmentPose_%1_%2", netId _medic, _poseEpoch]] call CBA_fnc_removeGlobalEventJIP;
        private _canExit = alive _medic && {isNull objectParent _medic} && {!(_medic getVariable ["ACE_isUnconscious",false])};
        private _rate = if (_canExit) then {call ACME_fnc_choreographyRate} else {1};
        private _packet = [_medic, _poseEpoch, ["release", "exit"] select _canExit, "", 2.1 / _rate, clientOwner, _rate];
        _packet call ACME_fnc_treatmentPoseSync;
        ["ACME_treatmentPoseSync", _packet] call CBA_fnc_globalEvent;
    };

    // Use the authored Putdown exit, the same provider animation family used to return a patient to supine.
    if (_ownsPose && {alive _medic} && {local _medic} && {isNull objectParent _medic}
        && {!(_medic getVariable ["ACE_isUnconscious",false])}) then {
        private _exit = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";
        private _rest = "AmovPknlMstpSnonWnonDnon";
        private _exitSerial = (_medic getVariable ["ACME_headElev_manualExitSerial",0]) + 1;
        _medic setVariable ["ACME_headElev_manualExitSerial",_exitSerial,false];
        _medic setUnitPos "MIDDLE";
        [_medic,_exit,2] call ACME_fnc_doAnim;

        private _releaseTime = missionNamespace getVariable ["ACME_headElev_seqReleaseTime", 2.1 / (call ACME_fnc_choreographyRate)];
        if !(_releaseTime isEqualType 0 && {finite _releaseTime} && {_releaseTime > 0.2}) then {_releaseTime = 2.1 / (call ACME_fnc_choreographyRate);};
        [{
            params ["_m","_serial","_rest"];
            if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}
                || {_m getVariable ["ACE_isUnconscious",false]}) exitWith {};
            if ((_m getVariable ["ACME_headElev_manualExitSerial",-1]) != _serial) exitWith {};
            if ([_m] call ACME_fnc_providerStanceOwned) exitWith {};
            [_m,_rest,2] call ACME_fnc_doAnim;
            _m setUnitPos "AUTO";
        }, [_medic,_exitSerial,_rest], _releaseTime] call CBA_fnc_waitAndExecute;
    };

    [_patient, "headElevHoldRelease", [_medic, _patient, _token]] call ACME_fnc_ownerDispatch;
}, {
    params ["_medic", "_patient", "_bodyPart", "_extra"];
    private _token = _extra select 0;

    private _hold = _patient getVariable ["ACME_headElev_hold", []];
    private _move = ["MoveForward","MoveBack","TurnLeft","TurnRight","MoveLeft","MoveRight","MoveFastForward","MoveSlowForward"] findIf {
        (inputAction _x) > 0.05
    } >= 0;

    private _leases = _patient getVariable ["ACME_headElev_treatments", createHashMap];
    private _animLock = _patient getVariable ["ACME_patientAnimLock", []];
    private _lockSource = _animLock param [1,"",[""]];
    private _lockPriority = _animLock param [3,0,[0]];
    private _lockUntil = _animLock param [4,-1,[0]];
    private _foreignPatientAnim = (_lockUntil isEqualType 0) && {_lockUntil > serverTime}
        && {_lockPriority >= 2}
        && {!(_lockSource in ["head-elev-lower","head-elev-flat"])};

    if (!alive _patient
        || {!(_patient getVariable ["ACME_headElevated", false])}
        || {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _token}
        || {(_hold param [0,objNull,[objNull]]) isNotEqualTo _medic}
        || {_patient getVariable ["ACME_headElev_Suspended", false]}
        || {_move}
        || {(count _leases) > 0}
        || {_foreignPatientAnim}
        || {[_patient] call ACM_core_fnc_cprActive}
        || {[_patient] call ACM_core_fnc_bvmActive}) then {
        ACM_core_ContinuousAction_Active = false;
    };
}, false, -1, true] call ACM_core_fnc_beginContinuousAction;
