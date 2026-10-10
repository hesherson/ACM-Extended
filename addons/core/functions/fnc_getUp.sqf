// Compile-time override of ACM_core_fnc_getUp.
// Phase 142: Get Up is a patient-local release transaction and MUST be able to leave ACM_LyingState.
//
// ACM_LyingState intentionally has no ConnectTo/InterpolateTo exits. The stock ACM Get Up therefore used ACE
// doAnimation priority 2, whose switchMove fallback is the engine-state repair that actually breaks out of the
// isolated lying state. A previous ACME pass changed this to the normal priority-1 animation queue to avoid snaps.
// That made the action consume ACM_core_Lying_State while playMoveNow could never leave ACM_LyingState, producing
// an awake casualty who was medically functional but permanently glued to the floor. Zeus unconscious toggling
// appeared to fix it because ACE's wake path also uses the priority-2 repair.
//
// Get Up deliberately bypasses ACME_fnc_animQueue because that queue defaults to priority 1 and cannot escape the isolated ACM_LyingState.
// Get Up is one of the very few places where priority 2 is deliberate. Normal treatment/provider animations still
// use the authored move graph. This function is repairing an isolated/dead/unconscious engine state, not entering a
// treatment pose.
params ["_patient", ["_authorized", true, [false]], ["_initiator", objNull, [objNull]]];
if (isNull _patient) exitWith {};
// Existing Get Up actions call this with two arguments. Capture the player who actually pressed the action before
// the request is routed to the casualty owner, so HPMK recovery goes to the correct inventory.
if (isNull _initiator && {hasInterface} && {!isNil "ACE_player"} && {!isNull ACE_player}) then {
    _initiator = ACE_player;
};
if (!local _patient) exitWith {
    ["ACM_core_getUpRequest", [_patient, _authorized, _initiator], _patient] call CBA_fnc_targetEvent;
};
if (!_authorized) exitWith {};

// Get Up may never mutate a casualty while ACE dragging/carrying owns their transform. Clearing lying state or
// switchMove'ing an attached casualty corrupts the carry transaction and can make the entity disappear on peers.
private _carryOwner = attachedTo _patient;
private _carryAnim = toLowerANSI animationState _patient;
private _carryOwned = !isNull _carryOwner || {(_carryAnim find "carried") >= 0};
if (_carryOwned) exitWith {
    if (!isNull _initiator && {local _initiator}) then {
        ["Put the casualty down before using Get Up.", 2, _initiator] call ace_common_fnc_displayTextStructured;
    };
};

// A manually removed carrier may never survive an accepted Get Up transaction. Force it back on before the
// lying-state flag or patient animation is released.
if ((_patient getVariable ["ACME_manualPlateCarrierState", ""]) != "") then {
    [_patient, "getup"] call ACME_fnc_manualPlateCarrierAutoReturn;
};

// Zone 3 aortic occlusion is incompatible with weight bearing, but do not swallow the Get Up transaction. Let the
// casualty actually begin to rise; the owner-local 5 Hz Zone 3 watcher detects STAND/CROUCH, ragdolls them, and
// immediately settles them prone. That makes a failed attempt look physical instead of making the button appear dead.
if (_patient getVariable ["ACME_AAJT_zone3", false]) then {
    [_patient] call ACME_fnc_aajtDownedTick;
    if (_patient == ACE_player) then {
        ["Zone 3 AAJT-S compression prevents you from weight bearing.", 2, _patient] call ace_common_fnc_displayTextStructured;
    };
};

// Get Up and an HPMK are mutually exclusive. Clear it before the rise animation and return the reusable kit to
// the person who initiated Get Up. Self Get Up therefore returns it to the casualty; provider Get Up returns it
// to that provider. hpmkRemove owns the one-shot state clear and cross-owner inventory return.
if ((_patient getVariable ["ACME_hpmk_state", ""]) != "") then {
    [_initiator, _patient, true] call ACME_fnc_hpmkRemove;
};

// Head elevation owns the casualty's physical pose. Release it first, then retry the same local transaction.
if (_patient getVariable ["ACME_headElevated", false]) exitWith {
    [objNull, _patient] call ACME_fnc_headElevateStop;
    [{
        params ["_p", "_initiator"];
        if (isNull _p || {!alive _p} || {_p getVariable ["ACME_headElevated", false]}) exitWith {};
        _p setUnitPos "AUTO";
        [_p, true, _initiator] call ACM_core_fnc_getUp;
    }, [_patient, _initiator], (missionNamespace getVariable ["ACME_headElev_lowerAnimTime", 1.4]) + 0.15] call CBA_fnc_waitAndExecute;
};

private _wasLying = _patient getVariable ["ACM_core_Lying_State", false];
private _obtunded = (missionNamespace getVariable ["ACME_sys_obtunded", false])
    && {_patient getVariable ["ACME_obtunded", false]}
    && {!(_patient getVariable ["ACE_isUnconscious", false])};

private _releaseAnims = [
    "ainjppnemstpsnonwrfldnon",
    "acm_lyingstate",
    "unconscious",
    "deadstate",
    toLower (missionNamespace getVariable ["ACME_obtunded_fixedAnim", "ACME_ObtundedBack"]),
    toLower (missionNamespace getVariable ["ACME_obtunded_rollToBackAnim", "AinjPpneMstpSnonWrflDnon_rolltoback"])
];
private _as = toLower animationState _patient;
private _aceUnconAnim = (_as find "ace_medical_engine_uncon_anim") >= 0;

// The lying flag is the authoritative ACM reason for exposing Get Up. The animation/life-state fallbacks cover
// locality changes and wake paths where the visible pose survived longer than the bookkeeping flag.
private _canRelease = _wasLying
    || {_as in _releaseAnims}
    || {_aceUnconAnim}
    || {(!(_patient getVariable ["ACE_isUnconscious", false])) && {(stance _patient == "PRONE") || {lifeState _patient == "INCAPACITATED"}}};
if (!_canRelease) exitWith {};

// An early Get Up owns the exit; cancel the one-shot without a stale resting-pose callback.
private _wakeExit = (_as find "acme_wake") == 0;
if (!isNil "ACME_fnc_wakeAnimationStop") then {[_patient] call ACME_fnc_wakeAnimationStop;};

// Retire any stale ACME held/queued animation owner before the release. A stale reassert worker must never be able
// to put ACM_LyingState back after the user has accepted Get Up.
_patient setVariable ["ACME_animQ", [], false];
_patient setVariable ["ACME_animQEnd", 0, false];
_patient setVariable ["ACME_animQActive", false, false];
_patient setVariable ["ACME_dah_gen", (_patient getVariable ["ACME_dah_gen", 0]) + 1, false];

_patient setUnitPos "AUTO";
// If ACE says the casualty is awake, also clear a stale engine-level setUnconscious lock. This does not alter ACE's
// medical state; it only releases the vanilla animation/controller flag that can survive interrupted wake paths.
if (!(_patient getVariable ["ACE_isUnconscious", false])) then {
    _patient setUnconscious false;
};

// Only now consume the action. At this point the release transaction has been accepted and the engine repair below
// is guaranteed to run on the owning machine.
_patient setVariable ["ACM_core_Lying_State", false, true];
if (!isNil "ACME_fnc_aiProtectionSync") then {[_patient] call ACME_fnc_aiProtectionSync;};

private _roll = missionNamespace getVariable ["ACME_getUp_anim", "UnconsciousOutProne"];
private _nativeTime = missionNamespace getVariable ["ACME_getUp_animTime", 1.6];
private _runTime = _nativeTime;

if (_obtunded) then {
    _runTime = (missionNamespace getVariable ["ACME_obtunded_getUpTime", 5.5]) max _nativeTime;
    private _coef = (_nativeTime / _runTime) max 0.18 min 0.45;
    _patient setVariable ["ACME_obtunded_slowGetUp", true, false];
    _patient setAnimSpeedCoef _coef;
    [{
        params ["_p"];
        if (isNull _p || {!local _p}) exitWith {};
        _p setAnimSpeedCoef 1;
        _p setVariable ["ACME_obtunded_slowGetUp", false, false];
    }, [_patient], _runTime + 0.05] call CBA_fnc_waitAndExecute;
} else {
    _patient setAnimSpeedCoef 1;
};

// IMPORTANT: priority 2 is required here. ACM_LyingState has ConnectTo[] = {} and InterpolateTo[] = {}, so
// priority-1 playMoveNow can never leave it. ACE priority 2 tries playMoveNow and then switchMove only if necessary.
if (_wakeExit) then {
    // Only an accepted Get Up may exit the wake graph toward locomotion. A partial
    // blend preserves the early-interrupt transition without exposing an automatic
    // prone/get-up edge to AI during ordinary clip completion.
    _patient switchMove [_roll,0,0.25,false];
} else {[_patient, _roll, 2] call ACME_fnc_doAnim;};

// First repair backstop: if a different unconscious/dead-state controller won the same frame, clear the engine lock
// and re-run the exact stock ACM release. This is intentionally short so the action never appears to vanish silently.
[{
    params ["_p", "_roll"];
    if (isNull _p || {!alive _p} || {!local _p} || {_p getVariable ["ACE_isUnconscious", false]}
        || {_p getVariable ["ACM_core_Lying_State", false]}
        || {!isNull objectParent _p} || {!isNull attachedTo _p}
        || {((_p getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}
        || {_p getVariable ["ACME_headElevated",false]}
        || {_p getVariable ["ACM_airway_RecoveryPosition_State",false]}) exitWith {};
    private _state = toLower animationState _p;
    private _stuck = _state in ["acm_lyingstate", "unconscious", "deadstate"]
        || {(_state find "ace_medical_engine_uncon_anim") >= 0};
    if (!_stuck) exitWith {};
    _p setUnconscious false;
    _p setUnitPos "AUTO";
    [_p, _roll, 2] call ACME_fnc_doAnim;
}, [_patient, _roll], 0.15] call CBA_fnc_waitAndExecute;

// Final engine-state repair mirrors ACE's own wake-up safeguard. If the casualty is medically awake but an
// unconscious-family state still survived, force normal prone first. From there the unit is no longer controller-
// locked and can move/get up normally even if the authored roll itself was rejected by a third-party animation mod.
[{
    params ["_p"];
    if (isNull _p || {!alive _p} || {!local _p} || {_p getVariable ["ACE_isUnconscious", false]}
        || {_p getVariable ["ACM_core_Lying_State", false]}
        || {!isNull objectParent _p} || {!isNull attachedTo _p}
        || {((_p getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}
        || {_p getVariable ["ACME_headElevated",false]}
        || {_p getVariable ["ACM_airway_RecoveryPosition_State",false]}) exitWith {};
    private _state = toLower animationState _p;
    private _stuck = _state in ["acm_lyingstate", "unconscious", "deadstate"]
        || {(_state find "ace_medical_engine_uncon_anim") >= 0} || {(_state find "acme_wake") == 0};
    if (!_stuck) exitWith {};
    _p setUnconscious false;
    _p setUnitPos "AUTO";
    [_p, "AmovPpneMstpSnonWnonDnon", 2] call ACME_fnc_doAnim;
}, [_patient], 0.65] call CBA_fnc_waitAndExecute;
