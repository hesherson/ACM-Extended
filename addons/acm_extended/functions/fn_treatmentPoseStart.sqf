/* Owner of one provider-treatment episode. Work samples are native RTM seconds; preparation and
 * moving portions use the shared choreography rate. Clinical hold/inspection timers stay in real seconds.
 * The owner publishes run -> hold -> exit/release, and receivers reject reordered older operations.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_mode", "inspect", [""]],
    ["_window", -1, [0]],
    ["_patient", objNull, [objNull]]
];
if (isNull _medic || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {[_medic] call ACME_fnc_animBlocked}) exitWith {-1};

[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
// B56: a treatment pose replaces the medical-menu pose without an intermediate exit motion.
[_medic, true] call ACME_fnc_menuPoseStop;

private _main = switch (_mode) do {
    case "response": {"ACME_ResponseCheckWork"};
    case "airway": {"ACME_AirwayCheckWork"};
    // Chest-seal Flip intentionally uses the literal BI medic4 state.  The B73 wrapper changed the move-graph
    // entry and lost the characteristic flip theatre.  Crouch-first entry/empty-hands handling still comes from
    // this controller; only the actual work state is restored to the known-good literal animation.
    case "roll": {"AinvPknlMstpSnonWnonDnon_medic4"};
    // Carrier removal/restoration uses the exact same body-handling medic4 theatre as Flip,
    // but remains held until the patient lift/lower transaction explicitly hands off.
    case "chestAccess": {"AinvPknlMstpSnonWnonDnon_medic4"};
    case "inspect": {"ACME_ChestInspectWork"};
    case "chestSealWorkspace": {"ACME_ChestSealWorkspace"};
    case "junctional": {"ACME_JunctionalWork"};
    case "stethoscope": {"ACME_StethoscopeWork"};
    case "chestSeal": {"AinvPknlMstpSnonWrflDnon_medic3"};
    case "ncdSeat": {"AinvPknlMstpSnonWrflDnon_medic1"};
    case "pulse": {"ACME_StethoscopeWork"};
    case "torsoBandage": {"AinvPknlMstpSnonWrflDnon_medic4"};
    case "headBandageLeft": {"AinvPknlMstpSnonWrflDnon_medic0"};
    case "headBandageRight": {"AinvPknlMstpSnonWrflDr_medic2_old"};
    case "directPressureAction": {"AinvPknlMstpSnonWrflDnon_medic5"};
    default {"AinvPknlMstpSnonWrflDnon_medic4"};
};

// B72 provider stance invariant: all ordinary medical work is authored/forced from the unarmed crouch. Never
// substitute standing medicUp variants because the casualty happens to be upright. The ONLY intentional standing
// provider sequence is fn_headElevMedicSeq while DraggerBase performs the lift.
if (isNull _patient) then {_patient = missionNamespace getVariable ["ace_medical_gui_target", objNull];};
private _upright = false;

private _holdAt = (missionNamespace getVariable ["ACME_poseHoldAt", createHashMap]) getOrDefault [_mode, -1];
private _stopAfterHold = (missionNamespace getVariable ["ACME_poseStopAfterHold", createHashMap]) getOrDefault [_mode, -1];
if !(_holdAt isEqualType 0) then {_holdAt = -1;};
if !(_stopAfterHold isEqualType 0) then {_stopAfterHold = -1;};

private _epoch = (_medic getVariable ["ACME_treatmentPoseEpoch", 0]) + 1;
_medic setVariable ["ACME_treatmentPoseEpoch", _epoch, true];
_medic setVariable ["ACME_treatmentPoseEpisode", [_epoch, true], true];
private _exclusion = format ["ACME_treatmentPose_%1_%2", netId _medic, _epoch];
private _actionStarted = CBA_missionTime;
private _rate = call ACME_fnc_choreographyRate;
_medic setAnimSpeedCoef _rate;
private _speedJIP = format ["ACME_treatmentPose_%1_%2", netId _medic, _epoch];
["ACME_treatmentPoseSync", [_medic, _epoch, "run", "", -1, clientOwner, _rate], _speedJIP] call CBA_fnc_globalEventJIP;
[_speedJIP, _medic] call CBA_fnc_removeGlobalEventJIP;
// B101: when another intervention takes animation ownership from an active Direct Pressure hold, the provider is
// already in ACME's authored empty-hands medical theatre. currentWeapon may still report the selected rifle even
// though the visible DP state has weapons disabled. Do not run medicAnimationPrep again in that handoff or Arma
// plays a pointless weapon-away transition between DP and the incoming treatment pose.
private _dpPoseHandoff = (_medic getVariable ["ACME_DP_Active", false])
    && {(_medic getVariable ["ACME_DP_TreatmentBusy", false])};
// A physical Flip is still a real medical animation and must wait for a sidearm to finish holstering. The former
// roll fast-path used selectWeapon "" and could start medic4 under a pistol that was still visibly in the hands.
// Direct Pressure remains the one exception because its existing authored hold already owns empty-hand theatre.
private _prepDelay = if (_dpPoseHandoff) then {
    if (currentWeapon _medic != "") then {_medic selectWeapon "";};
    _medic setVariable ["ACME_medicAnimationPrep", ["empty_hands_ready", CBA_missionTime, ""], false];
    0
} else {
    [_medic] call ACME_fnc_medicAnimationPrep
};
if !(_prepDelay isEqualType 0) then {_prepDelay = 0;};
private _prepUntil = _actionStarted + (_prepDelay max 0);

// State layout:
//  0 epoch, 1 mode, 2 main, 3 stage, 4 stageStarted, 5 pfh, 6 owner, 7 exclusion,
//  8 waitUntil, 9 finiteWindow (informational), 10 actionStarted, 11 holdAt, 12 holdPhase,
//  13 lastHoldAssert, 14 holdStarted, 15 stopAfterHold, 16 upright (standing medicUp state in use), 17 moving animation rate
// Stages: -1 waiting for the one weapon stow, -2 playing the BI stance transition into the crouch,
//          0 legacy immediate start, 1 requested state entering, 2 running, 3 frozen hold.
private _state = [_epoch, _mode, _main, -1, _actionStarted, -1, clientOwner, _exclusion,
    _prepUntil, _window, _actionStarted, _holdAt, -1, -1, -1, _stopAfterHold, _upright, _rate];
_medic setVariable ["ACME_treatmentPoseState", _state];
// An accepted physical examination/preparation is actual care; merely viewing
// the initial medical menu never reaches this controller.
if (!isNull _patient && {_patient isNotEqualTo _medic}) then {
    _medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
};

// Retire stale ACE/ACME pose requests. This episode is the only ACME owner.
_medic setVariable ["ACME_animQ", []];
_medic setVariable ["ACME_animQEnd", 0];
_medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1];
[_medic, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;
if (!isNil "ace_advanced_fatigue_setAnimExclusions") then {
    ace_advanced_fatigue_setAnimExclusions pushBackUnique _exclusion;
};

private _fnStartMain = {
    params ["_medic", "_main", "_state"];
    _medic setUnitPos (["MIDDLE", "UP"] select (_state param [16, false]));
    // B73: priority 1 is playMoveNow only. It walks the move graph and can never fall through to switchMove,
    // so provider work always interpolates into the authored state instead of teleporting into frame zero.
    [_medic, _main, 1] call ACME_fnc_doAnim;
    _state set [3, 1];
    _state set [4, CBA_missionTime];
};

// Crouch first. A provider who is standing or prone plays the normal BI transition into the unarmed kneel and only
// then receives the requested state, so the RTM starts from the pose it was authored for.
private _fnEnter = {
    params ["_medic", "_main", "_state", "_fnStartMain"];
    private _transition = "";
    private _length = 0;
    // B72 leaves the upright slot false for medical work. Keep this branch only as hot-reload compatibility.
    if (_state param [16, false]) exitWith {[_medic, _main, _state] call _fnStartMain;};
    switch (stance _medic) do {
        case "STAND": {_transition = "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"; _length = 0.65;};
        case "PRONE": {_transition = "AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"; _length = 1.116;};
        default {};
    };
    if (_transition == "") exitWith {[_medic, _main, _state] call _fnStartMain;};
    _medic setUnitPos "MIDDLE";
    [_medic, _transition, 1] call ACME_fnc_doAnim;
    _state set [3, -2];
    _state set [4, CBA_missionTime];
    _state set [8, CBA_missionTime + (_length / (_state param [17, 1]))];
};

if (_prepDelay <= 0) then {
    [_medic, _main, _state, _fnStartMain] call _fnEnter;
};

private _pfh = [{
    params ["_args", "_pfh"];
    _args params ["_medic", "_epoch", "_exclusion", "_fnEnter", "_fnStartMain"];

    if (isNull _medic) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
        [_exclusion] call CBA_fnc_removeGlobalEventJIP;
        if (!isNil "ace_advanced_fatigue_setAnimExclusions") then {
            private _index = ace_advanced_fatigue_setAnimExclusions find _exclusion;
            if (_index >= 0) then {ace_advanced_fatigue_setAnimExclusions deleteAt _index;};
        };
    };

    private _state = _medic getVariable ["ACME_treatmentPoseState", []];
    if (_state isEqualTo [] || {(_state select 0) != _epoch}) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    if (!local _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
        || {[_medic] call ACME_fnc_animBlocked}) exitWith {
        [_medic, "", _epoch] call ACME_fnc_treatmentPoseStop;
    };

    private _mode = _state param [1, "inspect"];
    private _main = _state param [2, "AinvPknlMstpSnonWrflDnon_medic4"];
    private _stage = _state param [3, 0];
    private _stageStarted = _state param [4, CBA_missionTime];
    private _waitUntil = _state param [8, CBA_missionTime];
    private _actionStarted = _state param [10, CBA_missionTime];
    private _holdAt = _state param [11, -1];
    private _stopAfterHold = _state param [15, -1];
    private _rate = _state param [17, 1];
    private _current = toLower animationState _medic;
    private _now = CBA_missionTime;

    switch (_stage) do {
        case -1: {
            // Do not enter the medical RTM until both the logical selection and the visible skeleton are truly
            // empty-handed. In particular, currentWeapon can clear before a sidearm has visually left the hand.
            private _visuallyEmpty = (((_current find "wnon") >= 0) && {((_current find "snon") >= 0)})
                || {_current in ["acm_genericcontinuous", "acm_pronecontinuous"]};
            private _weaponReady = (currentWeapon _medic == "") && {_visuallyEmpty};
            if (_weaponReady && {_now >= _waitUntil}) then {
                [_medic, _main, _state, _fnStartMain] call _fnEnter;
            } else {
                // Never fall through into a malformed pistol-over-medical pose. A failed engine holster retires
                // this provider theatre cleanly rather than queuing another family of put-away animations.
                if (_now - _actionStarted >= 3.0) then {
                    [_medic, _mode, _epoch] call ACME_fnc_treatmentPoseStop;
                };
            };
        };

        case -2: {
            // The stance transition is a finite BI move. Start the requested state when it has had its length, or
            // earlier if the engine already reports the crouch idle.
            if (_now >= _waitUntil || {(_current find "amovpknlmstpsnonwnondnon") == 0}) then {
                [_medic, _main, _state] call _fnStartMain;
            };
        };

        case 0: {
            // Compatibility with a hot-reloaded state from an older controller: one start, no reassert loop.
            [_medic, _main, _state] call _fnStartMain;
        };

        case 1: {
            if (_current == toLower _main) then {
                _state set [3, 2];
                private _elapsed = 0;
                if (_holdAt >= 0) then {
                    private _nativeElapsed = _medic getUnitMovesInfo 1;
                    if (_nativeElapsed isEqualType 0 && {finite _nativeElapsed} && {_nativeElapsed >= 0}) then {
                        _elapsed = _nativeElapsed;
                    };
                };
                _state set [4, _now - (_elapsed / _rate)];
            } else {
                // Do not replay the requested state while it is entering. The former 0.10 s replay loop caused the
                // rapid repeating reported after TSP integration. Modes that freeze must reach the exact state.
                if (_now - _stageStarted > 0.75 && {_holdAt < 0}) then {
                    _state set [3, 2];
                    _state set [4, _now];
                };
                // A missed finite medic4 or a disconnected move-graph transition must not leave chest entry
                // pending forever. Retire only this still-owned presentation, without replaying the move.
                if (_mode == "chestAccess" && {_now - _stageStarted >= 4.5}) then {
                    [_medic, _mode, _epoch, true] call ACME_fnc_treatmentPoseStop;
                };
            };
        };

        case 2: {
            // Junctional packing/dressing is a true repeating work animation for the full progress timer.
            // The move class is looped, but some Arma animation transitions still fall out to crouch after one
            // native cycle. Reassert only if the junctional state actually exited, never on a fixed timer.
            if (_holdAt < 0) exitWith {
                if (_mode == "junctional" && {_current != toLower _main} && {_now - _stageStarted >= 0.20}) then {
                    [_medic, _main, 1] call ACME_fnc_doAnim;
                    _state set [4, _now];
                };
            };
            if (_current != toLower _main && {_mode != "chestAccess"}) exitWith {
                // A sparse frame can skip the finite roll's held sample entirely.
                // It was observed running in stage 1; after its authored work time
                // has elapsed, record completion without replaying that finished RTM.
                if (_mode == "roll" && {(_now - _stageStarted) * _rate >= _holdAt}) then {
                    _medic setVariable ["ACME_rollProviderCompletedEpoch", _epoch, false];
                    [_medic, _mode, _epoch] call ACME_fnc_treatmentPoseStop;
                };
            };
            // Owner-clock time since the requested state was first reported. This is the freeze rule the user set.
            private _elapsed = (_now - _stageStarted) * _rate;
            if (_current == toLower _main) then {
                private _nativeElapsed = _medic getUnitMovesInfo 1;
                if (_nativeElapsed isEqualType 0 && {finite _nativeElapsed} && {_nativeElapsed >= 0}) then {
                    _elapsed = _nativeElapsed;
                };
            };
            if (_elapsed < _holdAt) exitWith {};

            // Normalized phase for peers to seek to. Unknown duration means peers freeze in place instead.
            // After a long owner frame, chestAccess can have left its observed finite move. Seek its one held
            // sample using that move's configured duration, never the duration of the unrelated current idle.
            private _duration = if (_current == toLower _main) then {_medic getUnitMovesInfo 2} else {0};
            if !(_duration isEqualType 0) then {_duration = 0;};
            if (_duration <= 0) then {
                private _speed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _main >> "speed");
                if (_speed < 0) then {_duration = -_speed;};
            };
            private _knownDuration = _duration > 0;
            if (!_knownDuration) then {_duration = 1;};
            private _phase = (_holdAt / _duration) min 1;
            if (!_knownDuration) then {_phase = -1;};

            // B57: freeze the owning client directly first. The old path depended on the global CBA event
            // round-tripping back to the owner; that allowed the local animation to keep running/restart instead of
            // stopping at the requested sample. Peers still receive the synchronized held frame below.
            if (_phase >= 0) then {_medic switchMove [_main, _phase, 1, false];};
            _medic setAnimSpeedCoef 0;
            private _jip = format ["ACME_treatmentPose_%1_%2", netId _medic, _epoch];
            ["ACME_treatmentPoseSync", [_medic, _epoch, "hold", _main, _phase, clientOwner], _jip] call CBA_fnc_globalEventJIP;
            [_jip, _medic] call CBA_fnc_removeGlobalEventJIP;
            _state set [12, _phase];
            _state set [13, _now];
            _state set [14, _now];
            _state set [3, 3];
            // Flip must still see completion if the short roll hold auto-exits
            // before its next tick. The epoch prevents reuse by a later click.
            if (_mode == "roll") then {
                _medic setVariable ["ACME_rollProviderCompletedEpoch", _epoch, false];
            };
        };

        case 3: {
            // The frozen hold has a watchdog. It re-seeks one held frame, not a running animation, so it cannot
            // produce a finite-action restart loop. A mode with a stop delay ends itself from the frozen frame.
            private _phase = _state param [12, -1];
            private _lastAssert = _state param [13, -1];
            private _holdStarted = _state param [14, _now];
            if (_stopAfterHold >= 0 && {_now - _holdStarted >= _stopAfterHold}) exitWith {
                [_medic, _mode, _epoch] call ACME_fnc_treatmentPoseStop;
            };
            private _stateDrift = _current != toLower _main;
            private _speedDrift = getAnimSpeedCoef _medic != 0;
            if (_stateDrift || {_speedDrift}) then {
                // A speed-only disturbance does not need another switchMove. Re-seeking the exact frame every time
                // an external system nudged animSpeedCoef was visible as an auscultation camera snap. Only restore
                // the move when the animation state itself actually changed.
                if (_stateDrift && {_phase >= 0}) then {_medic switchMove [_main, _phase, 1, false];};
                _medic setAnimSpeedCoef 0;
                _state set [13, _now];
            };
        };
    };
}, 0, [_medic, _epoch, _exclusion, _fnEnter, _fnStartMain]] call CBA_fnc_addPerFrameHandler;

_state set [5, _pfh];
_epoch
