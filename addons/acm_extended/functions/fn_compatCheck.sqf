// A one-shot compatibility check. Keep results locally and show a warning when a dependency is missing.
// on why this exists: this addon does not hook ACM and ACE. in 26 files it forks them, and overrides/ is full of
// snapshots of somebody else's code, frozen at whatever version it was copied from. that is a liability, and it
// is a silent one, which is the worst kind.
// if ACM ships a fix to a function we forked, we keep running our stale copy forever and never get it.
// if ACM or ACE renames a variable, ACM's own code is updated and ours is not, so we read a default and carry on
// being subtly wrong.
// if another mod overrides the same function, the load order decides who wins, silently.
// none of that produces an error. nothing turns red. the sim quietly does the wrong thing, and someone finds out
// three sessions later when a patient dies for no reason. that is exactly how the atrial-tach into vf bug was
// found: a medic did everything right and could not explain what happened.
// this cannot prevent drift. what it can do is turn a silent failure into a loud one, at startup, before anyone has
// a casualty on the table. that is worth a great deal on a heavily modded server, where the load order is not
// something anyone fully controls.

if (!isServer && {!hasInterface}) exitWith {};
if (missionNamespace getVariable ["ACME_compatChecked", false]) exitWith {};
missionNamespace setVariable ["ACME_compatChecked", true];

private _missing = [];
private _version = missionNamespace getVariable ["ACME_infusion_version", "?"];

private _hasMarker = {
    params ["_name", "_marker"];
    private _code = missionNamespace getVariable [_name, {}];
    _code isEqualType {} && {(toLowerANSI str _code find toLowerANSI _marker) >= 0}
};

// dropObject_carry is deliberately not a function fork anymore. ACE's stoppedCarry event carries ACME's
// lying-state reconciliation, so ACE is free to own/recompile ace_dragging_fnc_dropObject_carry without a
// compatibility warning or a load-order repair race.

// functions we call directly. if one of these is gone, whatever calls it fails at the worst possible moment.
{
    if (isNil _x) then { _missing pushBack format ["FUNCTION %1", _x]; };
} forEach [
    "ace_map_fnc_determineMapLight",  // the minigame darkness.
    "ace_map_fnc_getUnitFlashlights",  // the light picker.
    "ace_map_fnc_switchFlashlight",
    "ace_common_fnc_addCanInteractWithCondition",
    "ace_medical_status_fnc_getBloodPressure",  // our handlecriticalvitals fork.
    "ACM_circulation_fnc_AED_CanAdministerShock",
    "ACM_circulation_fnc_AED_AdministerShock",
    "ACM_core_fnc_handleCriticalVitals"  // we no longer fork it, and our rhythm proxy depends on how it reasons.
];

// Verify the reconciled critical functions which must be ACME/ACM-owned at runtime.
// Do not require the ACE medical-status volume symbol here: ACE may finalize that symbol, while ACME's
// authoritative vitals path intentionally calls ACM_circulation_fnc_getBloodVolumeChange directly.
{
    _x params ["_name", "_marker"];
    if !([_name, _marker] call _hasMarker) then { _missing pushBack format ["STALE/OVERRIDDEN %1", _name]; };
} forEach [
    // Modal ACME procedures require ACM's treatment bridge. If ACE or another addon wins this symbol later,
    // chest-seal/thoracostomy/IV launchers fall back into generic ACE treatment/menu semantics.
    ["ace_medical_treatment_fnc_treatment", "ACME_ApplyChestSeal"],
    ["ACM_circulation_fnc_getBloodVolumeChange", "B106:volumeCanonical"],
    ["ace_medical_vitals_fnc_handleUnitVitals", "B106:vasoconstrictionPersist"],
    ["ACM_circulation_fnc_setIV", "B106:setIVReconciled"],
    ["ACM_airway_fnc_handleAirway", "B106:airwayWakeGuard"],
    ["ACM_airway_fnc_handleAirwayCollapse", "B125:airwayCollapseWakeClear"],
    ["ACM_core_fnc_getUpPrompt", "B106:getUpLifecycle"],
    ["ACM_core_fnc_addVehiclePatientActions", "B106:vehicleUnloadGuard"],
    ["ACM_disability_fnc_handleFracture", "B106:fracturePainChance"],
    ["ACM_damage_fnc_wrapBodyPartLocal", "B106:wrappedWoundReopen"],
    ["ace_dragging_fnc_canCarry", "B106:ace321Carry"],
    ["ace_dragging_fnc_canDrag", "B106:ace321Drag"],
    ["ace_interact_menu_fnc_compileMenuSelfAction", "B106:ace321SelfMenu"],
    ["ace_zeus_fnc_moduleUnconscious", "B106:aiUnconsciousGuard"]
];

// variable names we read off patients. these are stringly-typed in our overrides, because the macros are not
// available to us, so a rename upstream is invisible until it is not.
private _probe = [
    ["ace_medical_heartRate",                   80],
    ["ace_medical_inCardiacArrest",             false],
    ["ACM_circulation_Cardiac_RhythmState",     0],
    ["ACM_circulation_CirculationState",        true],
    ["ACM_core_CriticalVitals_State",           false]
];

// the handlecriticalvitals override is gone, and with it the load-order roulette it came with.
// we no longer fork that function, because we no longer need to: ACM's variable now only ever holds numbers ACM
// understands, since fn_rhythmset writes a proxy. ACM can therefore never read a value it does not recognize, so
// its critical-vitals watchdog can never arrest a patient for being in a rhythm it has never heard of.
// that is one fewer frozen copy of somebody else's code sitting in this addon quietly rotting, and one fewer thing
// that silently loses a load-order race. the right fix deleted the workaround instead of guarding it.

missionNamespace setVariable ["ACME_compatMissing", +_missing, false];
if (_missing isEqualTo []) exitWith {
    diag_log "[ACME COMPAT] OK: required runtime functions/markers verified";
};

diag_log format ["[ACME COMPAT] FAILED (%1): %2", count _missing, _missing joinString " | "];

if (hasInterface) then {
    [{
        params ["_issues"];
        private _detail = _issues joinString " | ";
        [format ["ACM Extended: %1 compatibility problem(s). Missing/stale required functions or overrides detected. %2", count _issues, _detail], 8]
            call ace_common_fnc_displayTextStructured;
    }, [+_missing], 12] call CBA_fnc_waitAndExecute;
};
