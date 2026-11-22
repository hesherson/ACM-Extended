/*
 * Server: the straps closed over the casualty of a litter that has them as models of their own (the Talon:
 * acmeStrapArcBare[], acmeStrapArcHpmk[] in its class, one model for each strap, in the order they are closed).
 * Each model is a simple object hung on the litter; the strap on the deck that was taken up for it is hidden
 * (acmeStrapArcSources[]: the animation source of each). The straps go with the litter: XEH_postInit.sqf removes
 * them when it is deleted.
 * With the HPMK opened over his chest (acmeStrapArcHpmkOpen[]) the straps that cross the chest are undone: their
 * place in the list holds an empty model, and the litter's own strap stays hidden.
 * Arguments: 0: litter, 1: the casualty is in the HPMK <BOOL>, or which set <NUMBER> (0 bare, 1 HPMK, 2 HPMK
 * opened over the chest), 2: how many of the straps are closed <NUMBER> (default: all).
 */
params ["_litter", "_wrapped", ["_count", -1]];
if (!isServer || {isNull _litter}) exitWith {};
private _cfg = configOf _litter;
if (_wrapped isEqualType true) then {_wrapped = [0, 1] select _wrapped;};
if (_wrapped == 2 && {(getArray (_cfg >> "acmeStrapArcHpmkOpen")) isEqualTo []}) then {_wrapped = 1;};
private _models = getArray (_cfg >> (["acmeStrapArcBare", "acmeStrapArcHpmk", "acmeStrapArcHpmkOpen"] select _wrapped));
private _sources = getArray (_cfg >> "acmeStrapArcSources");
if (_count < 0) then {_count = count _models;};
(_litter getVariable ["acme_strap_arcsFor", [0, 0]]) params ["_wasWrapped", "_wasCount"];
if (_wasWrapped isEqualType true) then {_wasWrapped = [0, 1] select _wasWrapped;};
private _straps = (_litter getVariable ["acme_strap_arcs", []]) select {!isNull _x};
if (_wasWrapped isEqualTo _wrapped && {_wasCount == _count} && {count _straps == _count}) exitWith {};
_litter setVariable ["acme_strap_arcsFor", [_wrapped, _count]];
// straps of the other fit, and straps that are open again
if (_wasWrapped isNotEqualTo _wrapped) then {
    {deleteVehicle _x} forEach _straps;
    _straps = [];
};
while {count _straps > _count} do {deleteVehicle (_straps deleteAt (count _straps - 1));};
{
    if (_forEachIndex < _count && {_forEachIndex >= count _straps}) then {
        private _model = _x;
        if (_model select [0, 1] == "\") then {_model = _model select [1];};
        private _strap = createSimpleObject [_model, getPosWorld _litter];
        _strap attachTo [_litter, [0, 0, 0]];
        _straps pushBack _strap;
    };
} forEach _models;
// The litter's own strap is hidden where a model has taken its place, and shown again where none has (a SKED has
// models for three of its straps over a bare casualty, and for all five over one in the HPMK).
{
    if (_x != "") then {_litter animateSource [_x, [0, 1] select (_forEachIndex < _count && {_forEachIndex < count _models}), true];};
} forEach _sources;
_litter setVariable ["acme_strap_arcs", _straps, true];
