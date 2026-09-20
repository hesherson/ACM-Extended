// start the visible raise sequence for both entry paths, the medical action and the transfusion-menu button.
// the ACE treatment system can skip unknown or long animations when the treatment is short, so the
// ACM_GenericContinuous phase is played here explicitly instead of through animationmedic.
params ["_medic"];
if (isNull _medic || {!local _medic}) exitWith {};

_medic setVariable ["ACME_hang_Raising", true];

// Raising and holding an IV bag uses both provider arms. If Direct Pressure is active, keep the DP session alive
// but suspend its clinical marker and looping pose until this Hang Bag maneuver is cancelled or fully lowered.
if (_medic getVariable ["ACME_DP_Active", false]) then {
    _medic setVariable ["ACME_DP_Paused", true, false];
    _medic setVariable ["ACME_DP_PauseTreatmentClass", "hangbag", false];
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
};
[_medic] call ACME_fnc_medicAnimationPrep;
_medic setUnitPos "MIDDLE";

// some weapon mods make a back-slung weapon clip the ground in the crouched hold pose and loop a rapid
// collision-audio smacking sound. fully removing the back weapons, the primary and the launcher, for the duration
// kills that collider, and they are restored with their full state in fn_hangbagstop, which the watchdog of the
// hold also calls on death, unconsciousness, a leash break or lowering.
// it falls back to the old on-back stow if removal is disabled. Publish the two removed slots once so death,
// disconnect or a locality transfer can restore the corpse/provider on whichever machine owns it afterward.
if ((missionNamespace getVariable ["ACME_hang_removeWeapon", true]) && {(primaryWeapon _medic != "") || {secondaryWeapon _medic != ""}}) then {
    private _ld = getUnitLoadout _medic;
    _medic setVariable ["ACME_hang_savedWeaponSlots", [_ld select 0, _ld select 1], true];
    _ld set [0, []];
    _ld set [1, []];
    _medic setUnitLoadout _ld;
} else {
    // The single entry preflight above already selected empty hands. Do not issue another stow request.
};

private _enterGeneric = {
    params ["_medic"];
    if (!isNull _medic && {_medic getVariable ["ACME_hang_Raising", false]} && {!(_medic getVariable ["ACME_hang_Active", false])}) then {
        [_medic, "ACM_GenericContinuous", 1.4] call ACME_fnc_doAnimHeld;
    };
};

// use the stock kneel transitions before entering ACM_GenericContinuous, so the beginning does not snap.
switch (stance _medic) do {
    case "STAND": {
        [_medic, "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1.4, 1] call ACME_fnc_doAnimHeld;
        [_enterGeneric, [_medic], 0.65] call CBA_fnc_waitAndExecute;
    };
    case "PRONE": {
        [_medic, "AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1.4, 1] call ACME_fnc_doAnimHeld;
        [_enterGeneric, [_medic], 1.116] call CBA_fnc_waitAndExecute;
    };
    default {
        [_medic, "ACM_GenericContinuous", 1.4] call ACME_fnc_doAnimHeld;
    };
};
