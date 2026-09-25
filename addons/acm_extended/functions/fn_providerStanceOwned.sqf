/* Return true when another live provider-side controller currently owns stance/animation.
 * This is used only by delayed cleanup callbacks. A callback from an ended action must never release setUnitPos
 * underneath a newer treatment, Direct Pressure hold, Hang Bag, CPR, medical-menu crouch or head-position sequence.
 * Clinical state is deliberately not inferred from life state; the provider being alive is checked by the caller. */
params [["_unit", objNull, [objNull]], ["_closingMenu", false, [false]]];
if (isNull _unit) exitWith {false};

if ((_unit getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []) exitWith {true};
if ((_unit getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []) exitWith {true};
if (_unit getVariable ["ACME_treatmentPreflightActive", false]) exitWith {true};
if (_unit getVariable ["ACME_chestAccessPreflightActive", false]) exitWith {true};
if ((_unit getVariable ["ACME_chestAccessProvider", []]) isNotEqualTo []) exitWith {true};
// A closed progress display can leave ACE's end-animation hint behind. That hint
// alone must not trap a medical-menu pose forever. Startup remains protected by
// the native rate reservation, and all other callers retain the conservative check.
if ((_unit getVariable ["ace_medical_treatment_endInAnim", ""]) != ""
    && {!_closingMenu || {!isNull (uiNamespace getVariable ["ace_common_dlgProgress", displayNull])}
        || {(_unit getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []}}) exitWith {true};
if (_unit getVariable ["ACME_rollProviderActive", false]) exitWith {true};
// A crashed/retired provider PFH must not hold every later stance cleanup hostage. Live B166 head-position
// theatre refreshes this heartbeat every frame; one second is deliberately far beyond a normal scheduling gap.
private _headSeen = _unit getVariable ["ACME_headElev_seqLastSeen", -1e6];
private _headOwned = (_unit getVariable ["ACME_headElev_seqActive", false])
    && {(CBA_missionTime - _headSeen) <= 1};
if (_headOwned) exitWith {true};
if ((_unit getVariable ["ACME_menuPose", []]) isNotEqualTo []) exitWith {true};
if (_unit getVariable ["ACME_hang_Raising", false]) exitWith {true};
if (_unit getVariable ["ACME_hang_Active", false]) exitWith {true};
if (_unit getVariable ["ACME_DP_InPose", false]) exitWith {true};
if (_unit getVariable ["ACME_DP_TreatmentBusy", false]) exitWith {true};
if (_unit getVariable ["ACM_circulation_isPerformingCPR", false]) exitWith {true};

// Continuous actions are client-owned mission state (BVM, stethoscope, etc.), so only read it for the local player.
// Continuous actions refresh LastSeen at least every two seconds. Ignore an orphaned global flag here so an old
// BVM/manual-hold generation cannot indefinitely block menu/treatment stance cleanup while the recovery path
// clears the actual global gate.
private _session = _unit getVariable ["ACM_core_ContinuousAction_Session", []];
private _lastSeen = _unit getVariable ["ACM_core_ContinuousAction_LastSeen", -1e6];
private _continuousOwned = hasInterface && {!isNil "ACE_player"} && {_unit isEqualTo ACE_player}
    && {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}
    && {(count _session) >= 2}
    && {(CBA_missionTime - _lastSeen) <= 4};
if (_continuousOwned) exitWith {true};

false
