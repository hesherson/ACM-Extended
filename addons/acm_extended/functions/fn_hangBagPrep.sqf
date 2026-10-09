// start the visible raise sequence for both entry paths, the medical action and the transfusion-menu button.
// the ACE treatment system can skip unknown or long animations when the treatment is short, so the
// ACM_GenericContinuous phase is played here explicitly instead of through animationmedic.
params ["_medic"];
if (isNull _medic || {!local _medic}) exitWith {};
// B265: a duplicate preparation is not another equipment transaction. An
// unresolved earlier snapshot must be recovered BEFORE touching new weapons.
if (_medic getVariable ["ACME_hang_Raising", false]) exitWith {};
if ((_medic getVariable ["ACME_hang_savedWeaponSlots", []]) isNotEqualTo []) exitWith {
    ["Hang Bag: previous weapon return is incomplete. Resolve it before starting again.", 4, _medic]
        call ace_common_fnc_displayTextStructured;
};

private _prone = ([_medic, "AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation) == "AmovPpneMstpSnonWnonDnon";
private _prepToken = (_medic getVariable ["ACME_hang_PrepToken", 0]) + 1;
private _localityEpoch = _medic getVariable ["ACME_providerLocalityEpoch", 0];
_medic setVariable ["ACME_hang_PrepToken", _prepToken];
_medic setVariable ["ACME_hang_Prone", _prone];
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
_medic setUnitPos (["MIDDLE", "DOWN"] select _prone);

// some weapon mods make a back-slung weapon clip the ground in the crouched hold pose and loop a rapid
// collision-audio smacking sound. fully removing the back weapons, the primary and the launcher, for the duration
// kills that collider, and they are restored with their full state in fn_hangbagstop, which the watchdog of the
// hold also calls on death, unconsciousness, a leash break or lowering.
// it falls back to the old on-back stow if removal is disabled. Publish the two removed slots once so death,
// disconnect or a locality transfer can restore the corpse/provider on whichever machine owns it afterward.
if ((missionNamespace getVariable ["ACME_hang_removeWeapon", true]) && {(primaryWeapon _medic != "") || {secondaryWeapon _medic != ""}}) then {
    // Preserve the exact original weapon slots, including magazines with
    // their partial ammo, before changing any gear. Only remove the two
    // weapons, never rebuild the unit's uniform/hidden selection meshes.
    private _ld = getUnitLoadout _medic;
    private _slots = [_ld select 0, _ld select 1];
    _medic setVariable ["ACME_hang_savedWeaponSlots", _slots, true];
    _medic setVariable ["ACME_hang_weaponRestoreOwned", [[], []], true];
    if (primaryWeapon _medic != "") then {_medic removeWeapon (primaryWeapon _medic);};
    if (secondaryWeapon _medic != "") then {_medic removeWeapon (secondaryWeapon _medic);};
} else {
    // The single entry preflight above already selected empty hands. Do not issue another stow request.
};

private _pose = [_medic, "ACM_GenericContinuous", _prone] call ACME_fnc_providerAnimation;
private _enterGeneric = {
    params ["_medic", "_pose", "_prepToken", "_localityEpoch"];
    if (isNull _medic || {!local _medic}
        || {(_medic getVariable ["ACME_hang_PrepToken", -1]) != _prepToken}
        || {(_medic getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch}) exitWith {};
    if (_medic getVariable ["ACME_hang_Raising", false] && {!(_medic getVariable ["ACME_hang_Active", false])}) then {
        _pose = [_medic, _pose] call ACME_fnc_providerAnimation;
        if (stance _medic == "PRONE" || {_pose == "ACM_ProneContinuous"}) then {_medic setVariable ["ACME_hang_Prone", true];};
        [_medic, _pose, 1.4, 1, true] call ACME_fnc_doAnimHeld;
    };
};

// Preserve a prone provider. Only a standing provider uses the authored kneel entry.
if (!_prone && {stance _medic == "STAND"}) then {
    [_medic, "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1.4, 1, true] call ACME_fnc_doAnimHeld;
    [_enterGeneric, [_medic, _pose, _prepToken, _localityEpoch], 0.65] call CBA_fnc_waitAndExecute;
} else {
    [_medic, _pose, 1.4, 1, true] call ACME_fnc_doAnimHeld;
};
