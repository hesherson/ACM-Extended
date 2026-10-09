// tear down hang bag locally. it is safe to call repeatedly.
// on cancel we play the lower-the-bag exit animation and keep the bag and iv line in hand until it finishes, then
// delete them and restore the weapon, so the bag visibly comes down instead of popping out of existence.
params [["_silent", false], ["_medic", ACE_player]];
if (isNull _medic) exitWith {};
if !(_medic getVariable ["ACME_hang_Active", false]) exitWith {};

private _patient = _medic getVariable ["ACME_hang_Patient", objNull];
private _episodeStart = _medic getVariable ["ACME_hang_Start", -1];
// A pending claim owns no props or held pose. Cancel it without touching the prior
// episode's captured visual teardown, and restore prep-held weapons even after death.
if !(_medic getVariable ["ACME_hang_Claimed", false]) exitWith {
    _medic setVariable ["ACME_hang_Active", false, true];
    private _pendingPFH = _medic getVariable ["ACME_hang_PFH", -1];
    if (_pendingPFH >= 0) then {[_pendingPFH] call CBA_fnc_removePerFrameHandler;};
    _medic setVariable ["ACME_hang_PFH", -1];
    {[_x, "keydown"] call CBA_fnc_removeKeyHandler;} forEach (_medic getVariable ["ACME_hang_KeyIDs", []]);
    _medic setVariable ["ACME_hang_KeyIDs", []];
    [_patient, "hangBagRelease", [_medic, _episodeStart]] call ACME_fnc_ownerDispatch;
    if (local _medic) then {
        [_medic] call ACME_fnc_hangBagPrepStop;
    } else {
        ["ACME_hangRestoreWeapons", [_medic, _episodeStart], _medic] call CBA_fnc_targetEvent;
    };
};
private _prone = _medic getVariable ["ACME_hang_Prone", false];
_prone = _prone || {([_medic, "AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation) == "AmovPpneMstpSnonWnonDnon"};
private _visualEpoch = _medic getVariable ["ACME_hang_VisualEpoch", -1];
private _visualJip = _medic getVariable ["ACME_hang_VisualJip", ""];

// Retire the held-loop generation before starting the authored exit. Otherwise fn_doAnimHeld can reassert the
// static hold after RMB/Escape and leave the player frozen/sliding in a standing animation.
if (local _medic) then { [_medic, ""] call ACME_fnc_doAnimHeld; };
_medic setVariable ["ACME_hang_Active", false, true];

// B264: weapon restoration no longer rebuilds the unit loadout; preserve
// uniform hidden selections while the existing bag lowering completes.
// immediate: stop all the per-frame machinery and the cancel prompt.
private _ownsInput = (uiNamespace getVariable ["ACME_HangInputMedic", objNull]) isEqualTo _medic;
[_medic, false] call ACME_fnc_hangBagInputLock;
if (_ownsInput) then {[false] call ACME_fnc_hangBagHint;};

private _pfh = _medic getVariable ["ACME_hang_PFH", -1];
if (_pfh >= 0) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
_medic setVariable ["ACME_hang_PFH", -1];

{ [_x, "keydown"] call CBA_fnc_removeKeyHandler; } forEach (_medic getVariable ["ACME_hang_KeyIDs", []]);
_medic setVariable ["ACME_hang_KeyIDs", []];

// capture the props, so the delayed teardown can delete them after the exit animation.
private _rope      = _medic getVariable ["ACME_hang_Rope", objNull];
private _anchor    = _medic getVariable ["ACME_hang_LineAnchor", objNull];
private _bagHelper = _medic getVariable ["ACME_hang_BagHelper", objNull];
private _bag       = _medic getVariable ["ACME_hang_Bag", objNull];

private _outAnim = [_medic, missionNamespace getVariable ["ACME_hang_outAnim", "ACME_Acts_JetsCrewaidFCrouchThumbup_out"], _prone] call ACME_fnc_providerAnimation;
private _playedOut = false;
if (local _medic && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])} && {isNull objectParent _medic} && {(toLower animationState _medic) find "jetscrewaidfcrouchthumbup" >= 0}) then {
    // The loop now exposes an explicit interpolateTo edge to this state, and the out state has a ConnectTo edge
    // back to normal crouch. Do not delete props or restore the loadout until this authored lower-bag move has
    // actually entered and completed, because setUnitLoadout/idle restoration can cancel it mid-frame.
    [_medic, _outAnim, 1] call ACME_fnc_doAnim;
    _playedOut = true;
};

private _returnPart = _medic getVariable ["ACME_hang_Part", missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""]];

private _teardown = {
    params ["_medic", "_rope", "_anchor", "_bagHelper", "_bag", "_playedOut", "_outAnim", "_patient", "_returnPart", "_silent", "_episodeStart", "_visualEpoch", "_visualJip", "_prone"];

    // Observers keep the props throughout the authored lowering animation, then retire this exact episode.
    if ((_medic getVariable ["ACME_hang_VisualEpisode", []]) isEqualTo [_visualEpoch, true]) then {
        _medic setVariable ["ACME_hang_VisualEpisode", [_visualEpoch, false], true];
    };
    if (_visualJip != "") then {[_visualJip] call CBA_fnc_removeGlobalEventJIP;};
    ["ACME_hangBagVisualSync", [_medic, _visualEpoch, "hide"]] call CBA_fnc_globalEvent;

    // Cosmetic/rope objects belong to the ended episode and are always safe to delete from the captured references.
    if (!isNull _rope) then { [_rope] call ACME_fnc_ivLineDestroy; };
    if (!isNull _bagHelper) then { detach _bagHelper; deleteVehicle _bagHelper; };
    if (!isNull _anchor) then { detach _anchor; deleteVehicle _anchor; };
    if (!isNull _bag) then { detach _bag; deleteVehicle _bag; };

    // B127: provider state is not an old prop. A second Hang Bag can be started while this authored lower animation
    // is still completing. Never let the old delayed teardown reset the new pose, loadout, Direct Pressure pause or
    // stance. ACME_hang_Start is the immutable episode fingerprint and remains changed even if the newer bag is
    // subsequently lowered before this callback runs.
    private _sameEpisode = (_medic getVariable ["ACME_hang_Start", -2]) == _episodeStart;
    private _providerCanRestore = _sameEpisode && {!(_medic getVariable ["ACME_hang_Active", false])};

    // Equipment restoration is independent of animation/life state. A dead provider is still lootable and must
    // get the primary/launcher which Hang Bag temporarily removed. Locality transfer routes the one-shot restore.
    if (_providerCanRestore) then {
        if (local _medic) then {
            [_medic, _episodeStart] call ACME_fnc_hangBagRestoreWeapons;
        } else {
            ["ACME_hangRestoreWeapons", [_medic, _episodeStart], _medic] call CBA_fnc_targetEvent;
        };
    };

    if (_providerCanRestore && {local _medic} && {alive _medic} && {_medic isEqualTo ACE_player}
        && {!([_medic] call ACME_fnc_providerStanceOwned)}) then {
        _medic enableAI "ANIM";
        // Normal path: the authored out move has already connected itself to crouch. Fallback path: if the move
        // graph never entered/left the out state within the bounded wait below, explicitly recover to crouch so
        // a provider can never remain trapped in a cinematic state.
        private _state = toLower animationState _medic;
        if (!_playedOut || {(_state find "jetscrewaidfcrouchthumbup") >= 0}) then {
            [_medic, [_medic, "AmovPknlMstpSnonWnonDnon", _prone] call ACME_fnc_providerAnimation, 1] call ACME_fnc_doAnim;
        };
        _medic selectWeapon "";
        _medic setUnitPos (["MIDDLE", "DOWN"] select (_prone || {stance _medic == "PRONE"}));

        // MIDDLE is only the safe crouched handoff. Release the stance lock once the authored exit has settled, but
        // only if the same ended episode still owns provider cleanup.
        [{
            params ["_m", "_episodeStart"];
            if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}) exitWith {};
            if ((_m getVariable ["ACME_hang_Start", -2]) != _episodeStart) exitWith {};
            if (_m getVariable ["ACME_hang_Active", false]) exitWith {};
            if ([_m] call ACME_fnc_providerStanceOwned) exitWith {};
            _m setUnitPos "AUTO";
        }, [_medic, _episodeStart], 0.85] call CBA_fnc_waitAndExecute;
    };

    if (_providerCanRestore && {(_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == "hangbag"}) then {
        _medic setVariable ["ACME_DP_Paused", false, false];
        _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
        _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
    };

    if (!_silent && {!isNull _patient} && {_providerCanRestore} && {alive _medic} && {_medic isEqualTo ACE_player}) then {
        [{
            params ["_medic", "_patient", "_bp", "_episodeStart"];
            if (isNull _medic || {isNull _patient}) exitWith {};
            if ((_medic getVariable ["ACME_hang_Start", -2]) != _episodeStart) exitWith {};
            if !(_medic getVariable ["ACME_hang_Active", false]) then {
                [_medic, _patient, _bp] call ACM_circulation_fnc_openTransfusionMenu;
            };
        }, [_medic, _patient, _returnPart, _episodeStart], 0.10] call CBA_fnc_waitAndExecute;
    };
};

private _cleanupArgs = [_medic, _rope, _anchor, _bagHelper, _bag, _playedOut, _outAnim, _patient, _returnPart, _silent, _episodeStart, _visualEpoch, _visualJip, _prone];
if (_playedOut) then {
    // First wait until playMoveNow reaches the authored out state. Then wait until the state leaves naturally via
    // its ConnectTo edge. Both waits are bounded; timeout still runs the same safe teardown/recovery path.
    [{
        params ["_medic", "_outAnim"];
        isNull _medic || {(toLower animationState _medic) == (toLower _outAnim)}
    }, {
        params ["_medic", "_outAnim", "_teardown", "_cleanupArgs"];
        if (isNull _medic) exitWith { _cleanupArgs call _teardown; };
        [{
            params ["_medic", "_outAnim"];
            isNull _medic || {(toLower animationState _medic) != (toLower _outAnim)}
        }, {
            params ["_medic", "_outAnim", "_teardown", "_cleanupArgs"];
            _cleanupArgs call _teardown;
        }, _this, 3, {
            params ["_medic", "_outAnim", "_teardown", "_cleanupArgs"];
            _cleanupArgs call _teardown;
        }] call CBA_fnc_waitUntilAndExecute;
    }, [_medic, _outAnim, _teardown, _cleanupArgs], 0.75, {
        params ["_medic", "_outAnim", "_teardown", "_cleanupArgs"];
        _cleanupArgs call _teardown;
    }] call CBA_fnc_waitUntilAndExecute;
} else {
    _cleanupArgs call _teardown;
};

// clear the references and the state now. the delayed block holds its own copies.
_medic setVariable ["ACME_hang_Rope", objNull];
_medic setVariable ["ACME_hang_LineAnchor", objNull];
_medic setVariable ["ACME_hang_BagHelper", objNull];
_medic setVariable ["ACME_hang_Bag", objNull];
_medic setVariable ["ACME_hang_RopeShown", false, true];
_medic setVariable ["ACME_hang_Pose", nil];
_medic setVariable ["ACME_hang_PoseRetryAt", nil];
_medic setVariable ["ACME_hang_Raising", false];

if (!isNull _patient) then {
    // Release only this exact claim. A delayed stop from an earlier episode cannot clear a newer Hang Bag.
    [_patient, "hangBagRelease", [_medic, _episodeStart]] call ACME_fnc_ownerDispatch;
};
_medic setVariable ["ACME_hang_Claimed", false, false];
_medic setVariable ["ACME_hang_ClaimRequestedAt", 0, false];
if (!_silent) then {
    ["IV bag lowered.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
