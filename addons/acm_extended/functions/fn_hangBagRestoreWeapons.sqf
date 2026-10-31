/* B264: restore only the temporarily removed primary/launcher slots.
 * Never invoke setUnitLoadout: third-party uniforms derive gloves, sleeves,
 * boots and camouflage from model hidden selections not stored in unitLoadout.
 * Keep exact weapon/attachment/loaded-mag snapshots across owner migration.
 * Do not clobber a different weapon equipped during the Hang Bag episode.
 */
// Native suppression/add/repayment must not yield between cargo ownership
// changes. The normal callers are unscheduled; preserve that same transaction
// boundary when an owner or extension calls this helper from scheduled code.
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_hangBagRestoreWeapons; false};
    _result
};
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

// B269: addWeapon can take a compatible spare from ANY carried container.
// Temporarily suppress only those exact class/ammo cargo instances, then put
// them back in the same container after the saved loaded magazines are added.
// Do not use removeMagazines: a different held weapon may share the class.
// A rejected cargo return remains a replicated per-slot debt. A new owner may
// retry the return without creating the weapon or its loaded magazines again.
private _cargoDebt = +(_medic getVariable ["ACME_hang_weaponRestoreCargo", [[], []]]);
if (count _cargoDebt != 2) exitWith {false};
private _cargoAnomaly = (_medic getVariable ["ACME_hang_weaponRestoreCargoAnomaly", false]) isNotEqualTo false;
if (_cargoAnomaly) exitWith {false};
private _magCount = {
    params ["_container", "_magazine"];
    if (isNull _container) exitWith {0};
    {_x isEqualTo _magazine} count (magazinesAmmoCargo _container)
};
private _returnCargo = {
    params ["_slotIndex"];
    private _pending = [];
    {
        _x params ["_container", "_class", "_ammo"];
        if (_cargoAnomaly || {isNull _container}) then {
            _pending pushBack _x;
        } else {
            private _before = [_container, [_class, _ammo]] call _magCount;
            _container addMagazineAmmoCargo [_class, 1, _ammo];
            private _after = [_container, [_class, _ammo]] call _magCount;
            if (_after <= _before) then {_pending pushBack _x;};
            // Never repay an already observed insertion again. An impossible
            // native delta retains a separate conflict marker for inspection,
            // rather than a debt that would duplicate this returned magazine.
            if (_after != _before && {_after != _before + 1}) then {
                _cargoAnomaly = true;
                _medic setVariable ["ACME_hang_weaponRestoreCargoAnomaly",
                    [_container, _class, _ammo, _before, _after], true];
            };
        };
    } forEach (_cargoDebt select _slotIndex);
    _cargoDebt set [_slotIndex, _pending];
    _medic setVariable ["ACME_hang_weaponRestoreCargo", +_cargoDebt, true];
    _pending isEqualTo []
};
{[_x] call _returnCargo;} forEach [0, 1];
if (_cargoAnomaly) exitWith {false};

// B265: remember only a partial slot THIS restore created. On a retry we
// may fill missing parts only while that exact fingerprint is unchanged.
private _ownedSlots = +(_medic getVariable ["ACME_hang_weaponRestoreOwned", [[], []]]);
if (count _ownedSlots != 2) then {_ownedSlots = [[], []];};
private _allRestored = true;
private _restoreSlot = {
    params ["_slotIndex"];
    if (_cargoAnomaly) exitWith {_allRestored = false;};
    private _slot = +(_savedSlots select _slotIndex);
    if ((count _slot) == 0) exitWith {};
    if (count _slot != 7) exitWith {_allRestored = false;};
    private _weapon = _slot select 0;
    if (_weapon == "") exitWith {_allRestored = false;};
    // Do not add another weapon while an earlier suppression still owns cargo.
    if ((_cargoDebt select _slotIndex) isNotEqualTo []) exitWith {_allRestored = false;};
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

    if (_actual isEqualTo []) then {
        private _compatible = compatibleMagazines _weapon;
        private _suppressed = true;
        {
            private _container = _x;
            if (!isNull _container) then {
                private _spares = (magazinesAmmoCargo _container) select {(_x select 0) in _compatible};
                {
                    if (_suppressed) then {
                        _x params ["_class", "_ammo"];
                        private _before = [_container, [_class, _ammo]] call _magCount;
                        // Exact round-count removal is supported since Arma 3
                        // 2.14 (the fork requires 2.18). Preserve duplicates and
                        // empty magazines; never clear other magazine cargo.
                        _container addMagazineAmmoCargo [_class, -1, _ammo];
                        private _after = [_container, [_class, _ammo]] call _magCount;
                        for "_removed" from 1 to (_before - _after) do {
                            (_cargoDebt select _slotIndex) pushBack [_container, _class, _ammo];
                        };
                        _medic setVariable ["ACME_hang_weaponRestoreCargo", +_cargoDebt, true];
                        if (_after != _before - 1) then {_suppressed = false;};
                    };
                } forEach _spares;
                if ((magazinesAmmoCargo _container) findIf {(_x select 0) in _compatible} >= 0) then {
                    _suppressed = false;
                };
            };
        } forEach [uniformContainer _medic, vestContainer _medic, backpackContainer _medic];
        if (_suppressed) then {
            _medic addWeapon _weapon;
            private _created = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
            if ((_created param [0, ""]) == _weapon) then {
                // LinkedItems belong to the newly created gun, not the saved
                // snapshot. Remove only this fresh gun's default attachments.
                if (_slotIndex == 0) then {removeAllPrimaryWeaponItems _medic;}
                else {removeAllSecondaryWeaponItems _medic;};
            };
        };
    };
    _actual = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if ((_actual param [0, ""]) != _weapon) exitWith {
        [_slotIndex] call _returnCargo;
        _allRestored = false;
    };
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
        // getUnitLoadout's second loaded-magazine slot corresponds to the
        // second configured muzzle, even when the first is named, not "this".
        if (count _muzzles > 1) then {
            _medic addWeaponItem [_weapon,
                [_underbarrel select 0, _underbarrel select 1, _muzzles select 1], true];
        };
    };
    private _cargoReturned = [_slotIndex] call _returnCargo;
    // A modded weapon may reject an attachment/ammo. Retain the snapshot so
    // a later owner can retry or an operator can inspect the conflict.
    private _after = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if (_after isEqualTo _slot && {_cargoReturned} && {!_cargoAnomaly}) then {
        _savedSlots set [_slotIndex, []]; _ownedSlots set [_slotIndex, []];
    } else {
        _ownedSlots set [_slotIndex, +_after];
        _allRestored = false;
    };
    _medic setVariable ["ACME_hang_savedWeaponSlots", +_savedSlots, true];
    _medic setVariable ["ACME_hang_weaponRestoreOwned", +_ownedSlots, true];
};

{[_x] call _restoreSlot;} forEach [0, 1];
if (_cargoDebt isNotEqualTo [[], []]) then {_allRestored = false;};
if (_cargoAnomaly) then {_allRestored = false;};

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
_medic setVariable ["ACME_hang_weaponRestoreCargo", nil, true];
_medic setVariable ["ACME_hang_weaponRestoreCargoAnomaly", nil, true];
_medic setVariable ["ACME_hang_restoreWarningAt", -1000, false];
true
