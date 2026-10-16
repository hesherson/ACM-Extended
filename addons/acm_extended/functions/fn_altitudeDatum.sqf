/* Return the datum SUBTRACTED from raw getPosASL.
 * Explicit ACME datum mode >= 0 retains rawASL-minus-datum semantics.
 * Auto mode honors the live Eden elevation override, then ACE's additive map
 * elevation, then the world's elevationOffset. A declared additive base must
 * not also undergo heuristic authoring-offset subtraction.
 * With base zero, preserve the high terrain-plate correction. Only the costly
 * terrain minimum is cached; live mode/base/threshold changes are never stale.
 */
private _mode = missionNamespace getVariable ["ACME_altitude_datumMode", -1];
if !(_mode isEqualType 0 && {finite _mode}) then {_mode = -1;};
if (_mode >= 0) exitWith {_mode};

private _configuredBase = getNumber (configFile >> "CfgWorlds" >> worldName >> "elevationOffset");
if !(_configuredBase isEqualType 0 && {finite _configuredBase}) then {_configuredBase = 0;};
private _base = missionNamespace getVariable ["ace_common_mapAltitude", _configuredBase];
if !(_base isEqualType 0 && {finite _base}) then {_base = _configuredBase;};
private _override = missionNamespace getVariable ["ACME_ElevationOverride_Base", _base];
if ((missionNamespace getVariable ["ACME_ElevationOverride_Active", false])
    && {_override isEqualType 0} && {finite _override}) then {_base = _override;};
if (_base != 0) exitWith {-_base};

private _ws = worldSize;
if !(_ws isEqualType 0 && {finite _ws} && {_ws > 0}) exitWith {0};
private _cache = missionNamespace getVariable ["ACME_altitude_datumTerrain", []];
private _minimum = 0;
if (_cache isEqualType [] && {count _cache == 3}
    && {(_cache select 0) isEqualTo worldName} && {(_cache select 1) isEqualTo _ws}
    && {(_cache select 2) isEqualType 0} && {finite (_cache select 2)}) then {
    _minimum = _cache select 2;
} else {
    private _step = (_ws / 64) max 50;
    private _lowest = 1e9;
    private _seen = false;
    private _x = 0;
    while {_x <= _ws} do {
        private _y = 0;
        while {_y <= _ws} do {
            private _height = getTerrainHeightASL [_x, _y];
            if (_height isEqualType 0 && {finite _height}) then {
                _lowest = _lowest min _height;
                _seen = true;
            };
            _y = _y + _step;
        };
        _x = _x + _step;
    };
    _minimum = if (_seen) then {_lowest} else {0};
    missionNamespace setVariable ["ACME_altitude_datumTerrain", [worldName,_ws,_minimum]];
};
private _threshold = missionNamespace getVariable ["ACME_altitude_datumThreshold", 3000];
if !(_threshold isEqualType 0 && {finite _threshold}) then {_threshold = 3000;};
if (_minimum > _threshold) then {floor _minimum} else {0}
