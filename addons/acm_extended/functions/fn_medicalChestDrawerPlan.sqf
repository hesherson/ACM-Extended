/* Cabinet animation names come from the live assets. Each drawer gets an
   independent extension, with at least one visibly open. */
params ["_cabinet", ["_initial", false]];
private _isDrawer = {
    params ["_name"];
    _name = toLowerANSI _name;
    (_name find "drawer") >= 0 && {(_name find "hide") < 0} && {(_name find "lock") < 0}
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
private _phases = if (_initial) then {
    _names sort true;
    private _pattern = [0.63, 0, 0.42, 0.23];
    _names apply {_pattern select ((_names find _x) mod count _pattern)}
} else {
    private _randomPhases = _names apply {selectRandom [0, 0.23, 0.42, 0.63, 0.86]};
    _randomPhases set [floor random count _randomPhases, selectRandom [0.63, 0.86]];
    _randomPhases
};
[_names, _phases, _useSources]
