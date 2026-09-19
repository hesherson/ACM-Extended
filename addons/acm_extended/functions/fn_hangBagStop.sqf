// tear down hang bag locally. it is safe to call repeatedly.
// on cancel we play the lower-the-bag exit animation and keep the bag and iv line in hand until it finishes, then
// delete them and restore the weapon, so the bag visibly comes down instead of popping out of existence.
params [["_silent", false], ["_medic", ACE_player]];
if (isNull _medic) exitWith {};
if !(_medic getVariable ["ACME_hang_Active", false]) exitWith {};

private _patient = _medic getVariable ["ACME_hang_Patient", objNull];
private _episodeStart = _medic getVariable ["ACME_hang_Start", -1];
private _visualEpoch = _medic getVariable ["ACME_hang_VisualEpoch", -1];
private _visualJip = _medic getVariable ["ACME_hang_VisualJip", ""];

// Retire the held-loop generation before starting the authored exit. Otherwise fn_doAnimHeld can reassert the
// static hold after RMB/Escape and leave the player frozen/sliding in a standing animation.
if (local _medic) then { [_medic, ""] call ACME_fnc_doAnimHeld; };
_medic setVariable ["ACME_hang_Active", false, true];

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

private _outAnim = missionNamespace getVariable ["ACME_hang_outAnim", "ACME_Acts_JetsCrewaidFCrouchThumbup_out"];
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
    params ["_medic", "_rope", "_anchor", "_bagHelper", "_bag", "_playedOut", "_outAnim", "_patient", "_returnPart", "_silent", "_episodeStart", "_visualEpoch", "_visualJip"];

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

    if (_providerCanRestore && {local _medic} && {alive _medic} && {_medic isEqualTo ACE_player}) then {
        _medic enableAI "ANIM";
        // Normal path: the authored out move has already connected itself to crouch. Fallback path: if the move
        // graph never entered/left the out state within the bounded wait below, explicitly recover to crouch so
        // a provider can never remain trapped in a cinematic state.
        private _state = toLower animationState _medic;
        if (!_playedOut || {(_state find "jetscrewaidfcrouchthumbup") >= 0}) then {
            [_medic, "AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;
        };
        private _savedSlots = _medic getVariable ["ACME_hang_savedWeaponSlots", []];
        if !(_savedSlots isEqualTo []) then {
            private _ld = getUnitLoadout _medic;
            _ld set [0, _savedSlots select 0];
            _ld set [1, _savedSlots select 1];
            _medic setUnitLoadout _ld;
            _medic setVariable ["ACME_hang_savedWeaponSlots", nil];
        };
        _medic selectWeapon "";
        _medic setUnitPos "MIDDLE";

        // MIDDLE is only the safe crouched handoff. Release the stance lock once the authored exit has settled, but
        // only if the same ended episode still owns provider cleanup.
        [{
            params ["_m", "_episodeStart"];
            if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}) exitWith {};
            if ((_m getVariable ["ACME_hang_Start", -2]) != _episodeStart) exitWith {};
            if (_m getVariable ["ACME_hang_Active", false]) exitWith {};
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

private _cleanupArgs = [_medic, _rope, _anchor, _bagHelper, _bag, _playedOut, _outAnim, _patient, _returnPart, _silent, _episodeStart, _visualEpoch, _visualJip];
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

if (!isNull _patient && {(_patient getVariable ["ACME_hang_Medic", objNull]) isEqualTo _medic}) then {
    _patient setVariable ["ACME_hang_flowMult", 1, true];
    _patient setVariable ["ACME_hang_Medic", objNull, true];
};
if (!_silent) then {
    ["IV bag lowered.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
