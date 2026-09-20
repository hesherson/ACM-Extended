// Restore the exact primary/launcher slots temporarily removed by Hang Bag.
// Equipment belongs to the unit, not to the UI/player instance, so this intentionally works for corpses, AI and
// locality-transferred providers. Animation/stance cleanup stays in fn_hangBagStop and remains alive-player-only.
params [
    ["_medic", objNull, [objNull]],
    ["_episodeStart", -1, [0]]
];
if (isNull _medic || {!local _medic}) exitWith {false};
if (_episodeStart >= 0 && {(_medic getVariable ["ACME_hang_Start", -2]) != _episodeStart}) exitWith {false};
if (_medic getVariable ["ACME_hang_Active", false]) exitWith {false};

private _savedSlots = +(_medic getVariable ["ACME_hang_savedWeaponSlots", []]);
if ((count _savedSlots) < 2) exitWith {false};

private _ld = getUnitLoadout _medic;
if ((count _ld) < 2) exitWith {false};
_ld set [0, _savedSlots select 0];
_ld set [1, _savedSlots select 1];
_medic setUnitLoadout _ld;
// Public because ownership may have changed between removal and restoration. Clearing it prevents a later owner
// or stale disconnect callback from replaying an already-consumed loadout snapshot.
_medic setVariable ["ACME_hang_savedWeaponSlots", nil, true];
true
