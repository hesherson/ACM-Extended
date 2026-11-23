// recover from a true death of the megacode manikin. a unit that ACE has actually killed, where alive _d is false,
// cannot be revived in place. setdamage 0, fullheal and setunconsciousstate are all no-ops on a corpse, which is
// why the in-place reset failed and the keeper looped, re-announcing the death every pass, which is the popup
// spam.
// the only reliable recovery is to throw the corpse away and stand up a fresh manikin in the same spot through the
// proven spawn path, then re-point whoever had the panel open at the new manikin.
// it runs where the dead manikin is local, on the server. it is latched, so a double-call in the same beat cannot
// double-spawn.
// _this is [_old].
params [["_old", objNull]];
if (isNull _old || {!local _old}) exitWith {};
if (_old getVariable ["ACME_MC_respawning", false]) exitWith {};
_old setVariable ["ACME_MC_respawning", true, false];

// capture the placement, the rig objects and the operator before we delete anything.
private _pos     = getPosATL _old;
private _dir     = _old getVariable ["ACME_MC_spawnDir", getDir _old];  // the placement heading; a corpse can lie turned.
private _op      = _old getVariable ["ACME_MC_operatorClient", objNull];
private _laptop  = _old getVariable ["ACME_MC_laptop", objNull];
private _helpers = _old getVariable ["ACME_MC_helpers", []];
private _rope    = _old getVariable ["ACME_MC_rope", objNull];

// tear down the dead manikin and its whole rig. the old keeper pfh self-removes once its unit reads null.
if (!isNull _rope) then { ropeDestroy _rope };
{ if (!isNull _x) then { deleteVehicle _x }; } forEach _helpers;
if (!isNull _laptop) then { deleteVehicle _laptop };
deleteVehicle _old;

// stand up a clean manikin through the fully-tested spawn: a new body, laptop, cable and keeper, with the tuned
// offsets re-applied.
private _new = [_pos, _dir] call ACME_fnc_megacodeSpawn;
if (isNull _new) exitWith {
    objNull
};
_new setVariable ["ACME_MC_operatorClient", _op, true];

// if an operator had the panel open, swing it onto the new manikin and rebuild the current page. otherwise they
// will just re-open it from the new laptop. it is done on their client, so it reads their own open dialog and
// current page.
if (!isNull _op) then {
    [_new] remoteExec ["ACME_fnc_megacodePanelRetarget", _op];
};

_new
