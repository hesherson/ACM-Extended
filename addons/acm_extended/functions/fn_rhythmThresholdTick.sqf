/*
    ACM Extended rhythm threshold observer.

    Native ACM is the single authority for native rhythm entry/exit and cardiac-arrest
    thresholds.  This tick may create an optional custom SVT below ACM's fatal-high
    threshold and may perform an explicit medication conversion, but it never latches,
    restores, or second-guesses native VT/PVT/VF/asystole.  In particular, ACM's own
    handleCriticalVitals recovery path is allowed to clear VT back to sinus.
*/
if !(missionNamespace getVariable ["ACME_sys_rhythm", true]) exitWith {};
if !(missionNamespace getVariable ["ACME_rhythmThresholdsEnabled", true]) exitWith {};

private _now = CBA_missionTime;
private _acmHighHR = missionNamespace getVariable ["ACME_rhythmACMFatalHighHR", 220];
private _autoSVT = missionNamespace getVariable ["ACME_rhythmAutoSVTFromRateEnabled", false];
private _svtHR = missionNamespace getVariable ["ACME_rhythmCustomSVTHR", missionNamespace getVariable ["ACME_rhythmCriticalSVTHR", 190]];
private _svtSustain = missionNamespace getVariable ["ACME_rhythmCustomSVTSustainSec", 8];
private _shockGrace = missionNamespace getVariable ["ACME_rhythmNativeShockGraceSec", 10];

private _candidate = {
    params ["_u"];
    if (isNull _u || {!alive _u} || {!local _u}) exitWith {false};
    private _rhythmActive = _u getVariable ["ACME_rhythm_active",0];
    private _nativeRhythm = _u getVariable ["ACM_circulation_Cardiac_RhythmState",0];
    private _arrest = _u getVariable ["ace_medical_inCardiacArrest",false];
    private _thresholdPending = (_u getVariable ["ACME_rhythmThresholdKind",""]) != ""
        || {!isNil {_u getVariable "ACME_rhythmThresholdStart"}}
        || {(_u getVariable ["ACME_rhythmThresholdForced",""]) != ""};
    private _legacyHold = (_u getVariable ["ACME_rhythmNativeHoldKind",""]) != ""
        || {(_u getVariable ["ACME_rhythmNativeHoldRhythm",-1]) != -1}
        || {(_u getVariable ["ACME_rhythmNativeHighHRFloorUntil",0]) > 0};
    private _lidoCandidate = _nativeRhythm == 4 && {!_arrest}
        && {count (_u getVariable ["ace_medical_medications",[]]) > 0};
    private _hr = _u getVariable ["ace_medical_heartRate",0];
    private _autoCandidate = _autoSVT && {!_arrest} && {_rhythmActive == 0}
        && {_nativeRhythm in [0,5]} && {_hr >= _svtHR} && {_hr <= _acmHighHR};
    _rhythmActive >= 100 || {_thresholdPending} || {_legacyHold} || {_lidoCandidate} || {_autoCandidate}
};

private _fnc_clearLegacyNativeHold = {
    params ["_u"];
    if ((_u getVariable ["ACME_rhythmNativeHoldKind", ""]) != ""
        || {(_u getVariable ["ACME_rhythmNativeHoldRhythm", -1]) != -1}
        || {(_u getVariable ["ACME_rhythmNativeHighHRFloorUntil", 0]) > 0}) then {
        [_u, "", -1, true, true] call ACME_fnc_rhythmNativeHoldCommit;
        [_u, 0, false, false, false] call ACME_fnc_rhythmNativeHighHRFloorCommit;
    };
    _u setVariable ["ACME_rhythmNativeHoldSince", -1, false];
    _u setVariable ["ACME_rhythmNativeLastSeen", -1, false];
    _u setVariable ["ACME_rhythmNativeClearStart", -1, false];
};

private _patients = (missionNamespace getVariable ["ACME_rhythmThreshold_activePatients", []])
    select {!isNull _x && {alive _x} && {local _x}};
{
    private _u = _x;
    if (isNull _u || {!alive _u} || {!local _u}) then {continue};

    [_u] call _fnc_clearLegacyNativeHold;

    private _hr = _u getVariable ["ace_medical_heartRate", 0];
    private _rhythm = [_u] call ACME_fnc_rhythmGet;
    private _active = _u getVariable ["ACME_rhythm_active", 0];
    private _inArrest = _u getVariable ["ace_medical_inCardiacArrest", false];

    // A native critical rhythm always outranks an ACME custom overlay.  Release the overlay, then leave the native
    // rhythm alone; ACM's own state machine decides whether it deteriorates, persists, shocks, or recovers.
    private _nativeRhythm = _u getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
    if (_nativeRhythm in [1,2,3,4] && {_active >= 100}) then {
        [_u] call ACME_fnc_rhythmRelease;
        _active = 0;
        _rhythm = _nativeRhythm;
    };

    private _recentShock = (!isNil "ACM_circulation_fnc_recentAEDShock" && {[_u] call ACM_circulation_fnc_recentAEDShock})
        || {_now < (_u getVariable ["ACME_rhythmNativeShockGraceUntil", 0])};
    private _roscRecent = ((_u getVariable ["ACM_circulation_ROSC_Time", -9999]) + _shockGrace) > _now;
    if (_recentShock || {_roscRecent}) then {
        _u setVariable ["ACME_rhythmThresholdStart", nil];
        _u setVariable ["ACME_rhythmThresholdKind", ""];
        _u setVariable ["ACME_rhythmThresholdForced", "", false];
        continue;
    };

    // Therapeutic lidocaine is an explicit treatment path, not a threshold latch.  It may convert perfusing
    // monomorphic VT; arrest rhythms continue through the normal defibrillation/arrest machinery.
    private _lidoEff = 0;
    if (count (_u getVariable ["ace_medical_medications", []]) > 0) then {
        _lidoEff = [_u] call ACME_fnc_lidoEffectiveness;
    };
    if (_lidoEff > 0 && {_nativeRhythm == 4} && {!_inArrest}) then {
        [_u, 0] call ACME_fnc_rhythmSet;
        [_u, 0] call ACM_circulation_fnc_setCardiacArrestTargetRhythm;
        if (_active >= 100) then {[_u] call ACME_fnc_rhythmRelease;};
        [_u, [["aedPadsLastSync", -1]], true] call ACM_circulation_fnc_setRuntimeState;
        _u setVariable ["ACME_rhythmThresholdStart", nil];
        _u setVariable ["ACME_rhythmThresholdKind", ""];
        _u setVariable ["ACME_rhythmThresholdForced", "lidocaine VT conversion", false];
        continue;
    };

    // Clean up an orphaned custom display code.  This is bookkeeping only; it does not manufacture a native
    // critical rhythm or cardiac-arrest event.
    if (_active == 0 && {_rhythm >= 100}) then {
        [_u, 0] call ACME_fnc_rhythmSet;
        [_u, [["aedPadsLastSync", -1]], true] call ACM_circulation_fnc_setRuntimeState;
        _u setVariable ["ACME_rhythmThresholdStart", nil];
        _u setVariable ["ACME_rhythmThresholdKind", ""];
        continue;
    };

    // ACM owns <=40/>220 and every native arrest transition.  Optional auto-SVT is allowed only while perfusing,
    // below that fatal-high boundary, and with no custom/native critical rhythm already active.
    if (!_autoSVT || {_inArrest} || {_active != 0} || {!(_rhythm in [0,5])}) then {
        _u setVariable ["ACME_rhythmThresholdStart", nil];
        _u setVariable ["ACME_rhythmThresholdKind", ""];
        continue;
    };

    if (_hr < _svtHR || {_hr > _acmHighHR}) then {
        _u setVariable ["ACME_rhythmThresholdStart", nil];
        _u setVariable ["ACME_rhythmThresholdKind", ""];
        continue;
    };

    private _cur = _u getVariable ["ACME_rhythmThresholdKind", ""];
    private _start = _u getVariable ["ACME_rhythmThresholdStart", -1];
    if (_cur != "svt" || {_start < 0}) then {
        _u setVariable ["ACME_rhythmThresholdKind", "svt", false];
        _u setVariable ["ACME_rhythmThresholdStart", _now, false];
        continue;
    };
    if ((_now - _start) < _svtSustain) then {continue};

    [objNull, _u, 104, "SVT", (_hr min _acmHighHR)] call ACME_fnc_rhythmToggle;
    _u setVariable ["ACME_rhythmThresholdForced", "SVT", false];
} forEach _patients;
ACME_rhythmThreshold_activePatients = _patients select {[_x] call _candidate};
