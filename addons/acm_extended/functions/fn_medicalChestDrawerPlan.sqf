/* Cabinet animation names come from the live assets. Each drawer gets an
   independent extension, with one drawer visibly farther out than the rest. */
params ["_cabinet"];
// A padlocked drawer is named by the cabinet class and never slides out.
private _locked = (getArray (configOf _cabinet >> "acmeChestLockedDrawers")) apply {toLowerANSI _x};
private _isDrawer = {
    params ["_name"];
    _name = toLowerANSI _name;
    (_name find "drawer") >= 0 && {(_name find "hide") < 0} && {(_name find "lock") < 0} && {!(_name in _locked)}
};
private _sources = configProperties [
    configOf _cabinet >> "AnimationSources", "isClass _x && {getText (_x >> 'source') == 'user'}", true
];
_sources = (_sources apply {configName _x}) select {[_x] call _isDrawer};
private _useSources = _sources isNotEqualTo [];
private _names = if (_useSources) then {_sources} else {(animationNames _cabinet) select {[_x] call _isDrawer}};
if (_names isEqualTo []) exitWith {
    diag_log format ["[ACME] No drawer animations found for %1: %2", typeOf _cabinet, animationNames _cabinet];
    [[], [], false]
};
private _phases = _names apply {selectRandom [0, 0.23, 0.38, 0.52, 0.62]};
_phases set [floor random count _phases, 0.9];
[_names, _phases, _useSources]
