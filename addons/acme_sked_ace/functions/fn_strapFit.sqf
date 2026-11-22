/*
 * The straps of a litter are set to the casualty on it: close over a bare one, wider for one in the HPMK.
 *  - A litter whose straps are part of its model (the SKED): each strap is moved up or down by its animation
 *    source. The litter's class says by how much: acmeStrapFitBare[], acmeStrapFitHpmk[], one number (m) for
 *    each source in acmeStrapFitSources[]. The engine carries the settings to every machine.
 *  - A litter whose straps closed over the casualty are models of their own (the Talon, acmeStrapArcBare[] and
 *    acmeStrapArcHpmk[]): the server is asked to hang the right ones on it (fn_strapArcs.sqf).
 * Does nothing when the litter is already set for what the casualty wears now, so it can be called as often as
 * one likes (the pose guard calls it once a second where the casualty is local).
 * Arguments: 0: litter.
 */
params ["_litter"];
if (isNull _litter) exitWith {};
private _cfg = configOf _litter;
private _sources = getArray (_cfg >> "acmeStrapFitSources");
private _arcs = (getArray (_cfg >> "acmeStrapArcBare")) isNotEqualTo [];
if (_sources isEqualTo [] && {!_arcs}) exitWith {};
private _patient = _litter getVariable ["acme_sked_patient", objNull];
private _wrapped = !isNull _patient && {(vest _patient) in ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"]};
// (for the tests: other distances than the config's)
private _fit = missionNamespace getVariable ["acme_strap_fitTest", getArray (_cfg >> (["acmeStrapFitBare", "acmeStrapFitHpmk"] select _wrapped))];
// Which set of strap models: for a bare casualty, for one in the HPMK, or for one in the HPMK with the cover folded
// back off his chest (the straps that cross the chest are undone for that: fn_strapArcs.sqf).
private _set = [0, 1] select _wrapped;
if (_wrapped && {(vest _patient) in ["ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"]}
    && {(getArray (_cfg >> "acmeStrapArcHpmkOpen")) isNotEqualTo []}) then {_set = 2;};
private _key = [_set, _fit];
if ((_litter getVariable ["acme_strap_fitFor", []]) isEqualTo _key) exitWith {};
_litter setVariable ["acme_strap_fitFor", _key, true];
{
    // (a whole unit of the source moves a strap 1.25 m: measured in game, it is not what model.cfg's offsets say)
    _litter animateSource [_x, ((_fit param [_forEachIndex, 0]) / 1.25) max -1 min 1];
} forEach _sources;
if (_arcs) then {["acme_sked_strapArcs", [_litter, _set]] call CBA_fnc_serverEvent;};
