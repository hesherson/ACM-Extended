/* B264: restore only the temporarily removed primary/launcher slots.
 * Never invoke setUnitLoadout: third-party uniforms derive gloves, sleeves,
 * boots and camouflage from model hidden selections not stored in unitLoadout.
 * Keep exact weapon/attachment/loaded-mag snapshots across owner migration.
 * Do not clobber a different weapon equipped during the Hang Bag episode.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_episodeStart", -1, [0]]
];
if (isNull _medic || {!local _medic}) exitWith {false};
// A delayed owner-targeted restore may belong to an intentionally replaced
// kit. Reject it before reading or mutating any current equipment slots.
private _kitEpoch = _medic getVariable ["ACME_equipmentKitEpoch", 0];
if ((_medic getVariable ["ACME_hang_weaponKitEpoch", _kitEpoch]) != _kitEpoch) exitWith {false};
if (_episodeStart >= 0 && {(_medic getVariable ["ACME_hang_Start", -2]) != _episodeStart}) exitWith {false};
if (_medic getVariable ["ACME_hang_Active", false]) exitWith {false};
private _savedSlots = +(_medic getVariable ["ACME_hang_savedWeaponSlots", []]);
if ((count _savedSlots) < 2) exitWith {false};

// B265: remember only a partial slot THIS restore created. On a retry we
// may fill missing parts only while that exact fingerprint is unchanged.
private _ownedSlots = +(_medic getVariable ["ACME_hang_weaponRestoreOwned", [[], []]]);
if (count _ownedSlots != 2) then {_ownedSlots = [[], []];};
private _allRestored = true;
private _restoreSlot = {
    params ["_slotIndex"];
    private _slot = +(_savedSlots select _slotIndex);
    if ((count _slot) == 0) exitWith {};
    if (count _slot != 7) exitWith {_allRestored = false;};
    private _weapon = _slot select 0;
    if (_weapon == "") exitWith {_allRestored = false;};
    private _actual = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if (_actual isEqualTo _slot) exitWith {
        // Settle this slot immediately: later changes to it are NOT ours.
        _savedSlots set [_slotIndex, []]; _ownedSlots set [_slotIndex, []];
        _medic setVariable ["ACME_hang_savedWeaponSlots", +_savedSlots, true];
        _medic setVariable ["ACME_hang_weaponRestoreOwned", +_ownedSlots, true];
    };
    // Another mod may have installed a different rifle/launcher while the
    // bag was held. Never overwrite it; retain the saved slot for recovery.
    if (_actual isNotEqualTo [] && {
        (_ownedSlots select _slotIndex) isEqualTo []
        || {_actual isNotEqualTo (_ownedSlots select _slotIndex)}
    }) exitWith {_allRestored = false;};

    if (_actual isEqualTo []) then {_medic addWeapon _weapon;};
    _actual = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if ((_actual param [0, ""]) != _weapon) exitWith {_allRestored = false;};
    // Same slot encoding as getUnitLoadout:
    // [weapon, muzzle, pointer, optic, [mag,ammo], [GLmag,ammo], bipod].
    // Fill missing attachments only. Never replace an attachment another
    // addon put on the gun or refill a magazine after the player fired it.
    {
        private _wanted = _slot select _x;
        if (_wanted isEqualType "" && {_wanted != ""} && {(_actual param [_x, ""]) == ""}) then {
            _medic addWeaponItem [_weapon, _wanted, true];
        };
    } forEach [1, 2, 3, 6];

    private _primaryMag = _slot select 4;
    if (_primaryMag isEqualType [] && {count _primaryMag >= 2}
        && {(_primaryMag select 0) != ""} && {(_actual param [4, []]) isEqualTo []}) then {
        _medic addWeaponItem [_weapon, [_primaryMag select 0, _primaryMag select 1], true];
    };
    private _underbarrel = _slot select 5;
    if (_underbarrel isEqualType [] && {count _underbarrel >= 2}
        && {(_underbarrel select 0) != ""} && {(_actual param [5, []]) isEqualTo []}) then {
        private _muzzles = getArray (configFile >> "CfgWeapons" >> _weapon >> "muzzles");
        private _other = _muzzles select {_x != "this"};
        if (count _other > 0) then {
            _medic addWeaponItem [_weapon,
                [_underbarrel select 0, _underbarrel select 1, _other select 0], true];
        };
    };
    // A modded weapon may reject an attachment/ammo. Retain the snapshot so
    // a later owner can retry or an operator can inspect the conflict.
    private _after = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if (_after isEqualTo _slot) then {
        _savedSlots set [_slotIndex, []]; _ownedSlots set [_slotIndex, []];
    } else {
        _ownedSlots set [_slotIndex, +_after];
        _allRestored = false;
    };
    _medic setVariable ["ACME_hang_savedWeaponSlots", +_savedSlots, true];
    _medic setVariable ["ACME_hang_weaponRestoreOwned", +_ownedSlots, true];
};

{[_x] call _restoreSlot;} forEach [0, 1];

if (!_allRestored) exitWith {
    private _last = _medic getVariable ["ACME_hang_restoreWarningAt", -1000];
    if (CBA_missionTime - _last >= 3) then {
        diag_log format ["[ACME HANG B264] weapon slot restore incomplete; unit=%1 saved slots retained; actual=%2",
            netId _medic, (getUnitLoadout _medic) select [0, 2]];
        _medic setVariable ["ACME_hang_restoreWarningAt", CBA_missionTime, false];
    };
    false
};
// One-shot owner-local completion: an old disconnected client cannot restore
// again after the new owner cleared the replicated snapshot.
_medic setVariable ["ACME_hang_savedWeaponSlots", nil, true];
_medic setVariable ["ACME_hang_weaponRestoreOwned", nil, true];
_medic setVariable ["ACME_hang_restoreWarningAt", -1000, false];
true
