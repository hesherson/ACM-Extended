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
if (_episodeStart >= 0 && {(_medic getVariable ["ACME_hang_Start", -2]) != _episodeStart}) exitWith {false};
if (_medic getVariable ["ACME_hang_Active", false]) exitWith {false};
private _savedSlots = +(_medic getVariable ["ACME_hang_savedWeaponSlots", []]);
if ((count _savedSlots) < 2) exitWith {false};

private _allRestored = true;
for "_slotIndex" from 0 to 1 do {
    private _slot = +(_savedSlots select _slotIndex);
    if ((count _slot) == 0) then {continue};
    if (count _slot < 7) then {_allRestored = false; continue};
    private _weapon = _slot select 0;
    if (_weapon == "") then {continue};
    private _actual = (getUnitLoadout _medic) param [_slotIndex, [], [[]]];
    if (_actual isEqualTo _slot) then {continue};
    // Another mod may have installed a different rifle/launcher while the
    // bag was held. Never overwrite it; retain the saved slot for recovery.
    if !(_actual isEqualTo []) then {_allRestored = false; continue};

    _medic addWeapon _weapon;
    // Same slot encoding as getUnitLoadout:
    // [weapon, muzzle, pointer, optic, [mag,ammo], [GLmag,ammo], bipod].
    {
        if (_x isEqualType "" && {_x != ""}) then {
            _medic addWeaponItem [_weapon, _x, true];
        };
    } forEach [_slot select 1, _slot select 2, _slot select 3, _slot select 6];

    private _primaryMag = _slot select 4;
    if (_primaryMag isEqualType [] && {count _primaryMag >= 2}
        && {(_primaryMag select 0) != ""}) then {
        _medic addWeaponItem [_weapon, [_primaryMag select 0, _primaryMag select 1], true];
    };
    private _underbarrel = _slot select 5;
    if (_underbarrel isEqualType [] && {count _underbarrel >= 2}
        && {(_underbarrel select 0) != ""}) then {
        private _muzzles = getArray (configFile >> "CfgWeapons" >> _weapon >> "muzzles");
        private _other = _muzzles select {_x != "this"};
        if (count _other > 0) then {
            _medic addWeaponItem [_weapon,
                [_underbarrel select 0, _underbarrel select 1, _other select 0], true];
        };
    };
    // A modded weapon may reject an attachment/ammo. Retain the snapshot so
    // a later owner can retry or an operator can inspect the conflict.
    if !(((getUnitLoadout _medic) param [_slotIndex, [], [[]]]) isEqualTo _slot) then {
        _allRestored = false;
    };
};

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
_medic setVariable ["ACME_hang_restoreWarningAt", -1000, false];
true
