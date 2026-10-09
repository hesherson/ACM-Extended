// Restore the exact primary/launcher slots temporarily removed by Hang Bag.
// Equipment belongs to the unit, not to the UI/player instance, so this intentionally works for corpses, AI and
// locality-transferred providers. Animation/stance cleanup stays in fn_hangBagStop and remains alive-player-only.
// Weapons are re-added with addWeapon/addWeaponItem instead of setUnitLoadout, because setUnitLoadout rebuilds the
// uniform and resets hidden selections (gloves, boots, camo, sleeves).
params [
    ["_medic", objNull, [objNull]],
    ["_episodeStart", -1, [0]]
];
if (isNull _medic || {!local _medic}) exitWith {false};
if (_episodeStart >= 0 && {(_medic getVariable ["ACME_hang_Start", -2]) != _episodeStart}) exitWith {false};
if (_medic getVariable ["ACME_hang_Active", false]) exitWith {false};

private _savedSlots = +(_medic getVariable ["ACME_hang_savedWeaponSlots", []]);
if ((count _savedSlots) < 2) exitWith {false};

{
    // slot format: [weapon, muzzle, pointer, optic, [mag, ammo], [underbarrelMag, ammo], bipod]. empty slot is [].
    if (_x isEqualType [] && {count _x >= 7} && {(_x select 0) != ""}) then {
        private _slot = _x;
        private _weapon = _slot select 0;

        _medic addWeapon _weapon;

        // attachments: muzzle, pointer, optic, bipod
        {
            if (_x isEqualType "" && {_x != ""}) then {
                _medic addWeaponItem [_weapon, _x, true];
            };
        } forEach [_slot select 1, _slot select 2, _slot select 3, _slot select 6];

        // loaded magazine, keeping its exact ammo count
        private _mag = _slot select 4;
        if (_mag isEqualType [] && {count _mag >= 2} && {(_mag select 0) != ""}) then {
            _medic addWeaponItem [_weapon, [_mag select 0, _mag select 1], true];
        };

        // underbarrel (grenade launcher) magazine goes into the weapon's second muzzle
        private _mag2 = _slot select 5;
        if (_mag2 isEqualType [] && {count _mag2 >= 2} && {(_mag2 select 0) != ""}) then {
            private _muzzles = getArray (configFile >> "CfgWeapons" >> _weapon >> "muzzles");
            private _gl = _muzzles select {_x != "this"};
            if (count _gl > 0) then {
                _medic addWeaponItem [_weapon, [_mag2 select 0, _mag2 select 1, _gl select 0], true];
            };
        };
    };
} forEach _savedSlots;

// Public because ownership may have changed between removal and restoration. Clearing it prevents a later owner
// or stale disconnect callback from replaying an already-consumed loadout snapshot.
_medic setVariable ["ACME_hang_savedWeaponSlots", nil, true];
true
