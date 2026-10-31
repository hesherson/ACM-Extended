/* B287: server owns deployed cargo and its per-bag exposure together.
 * Unidentified same-class removals retain the oldest matching records; additions
 * inherit a recent released exposure, otherwise begin at this observation.
 */
params ["_box", ["_now", serverTime, [0]], ["_mode", "full", [""]]];
if (!isServer || {isNull _box} || {!finite _now}) exitWith {[]};
if !(_mode in ["full", "release"]) exitWith {[]};
if (_box getVariable ["ACME_coolerRetired", false]) exitWith {[]};
private _state = _box getVariable ["ACME_boxCoolerState", []];
private _previous = _state;
if (_box getVariable ["ACME_coolerPacking", false]) exitWith {
    if (count _state != 4) then {[]} else {[_state # 0, _state # 1, (_state # 2) apply {+_x}, _state # 3]}
};
private _base = _box getVariable ["ACME_boxCoolerClass", ""];
if (_base == "") then {
    _base = switch (typeOf _box) do {
        case "ACME_BloodCoolerBox_CSWB1U": {"ACME_BloodCooler_CSWB1U"};
        case "ACME_BloodCoolerBox_CSWB2U": {"ACME_BloodCooler_CSWB2U"};
        case "ACME_BloodCoolerBox_CSWB4U": {"ACME_BloodCooler_CSWB4U"};
        default {""};
    };
};
if (_base == "") exitWith {[]};
if (count _state != 4) then {
    private _start = _box getVariable ["ACME_boxCoolantStart", _now];
    _state = [_base, _start, [], _now];
};
private _advanced = [_state, _now] call ACME_fnc_coolerAdvance;
if (_advanced isEqualTo []) exitWith {[]};
private _counts = createHashMap;
{
    if (([_x] call ACME_fnc_coolerBagVolume) > 0) then {
        _counts set [_x, (_counts getOrDefault [_x, 0]) + 1];
    };
} forEach (itemCargo _box);
private _byClass = createHashMap;
{
    _x params ["_class", "_warm"];
    private _ages = _byClass getOrDefault [_class, []];
    _ages pushBack _warm;
    _byClass set [_class, _ages];
} forEach (_advanced # 2);
private _float = missionNamespace getVariable ["ACME_ccBagFloat", createHashMap];
private _ttl = missionNamespace getVariable ["ACME_bloodFloatTTL", 180];
private _entries = [];
{
    private _class = _x;
    private _ages = _byClass get _class;
    _ages sort false;
    private _wanted = _counts getOrDefault [_class, 0];
    {
        if (_forEachIndex < _wanted) then {_entries pushBack [_class, _x];}
        else {
            private _released = _float getOrDefault [_class, []];
            _released pushBack [_x, _now];
            _float set [_class, _released];
        };
    } forEach _ages;
    _counts set [_class, (_wanted - count _ages) max 0];
} forEach keys _byClass;
missionNamespace setVariable ["ACME_ccBagFloat", _float];
private _hasAdmissions = (keys _counts findIf {(_counts get _x) > 0}) >= 0;
if (_mode == "full" && {_hasAdmissions}) then {
    // A direct native cargo addition may have left a person's inventory before
    // the ordinary 60-second scan. Synchronize that release before matching
    // ages. This scan runs on cargo admissions, never on every cooler tick.
    if ((missionNamespace getVariable ["ACME_ccBoxAdmissionFrame", -1]) != diag_frameNo) then {
        missionNamespace setVariable ["ACME_ccBoxAdmissionFrame", diag_frameNo];
        [0, _box] call ACME_fnc_bloodColdChainTick;
    };
    _float = missionNamespace getVariable ["ACME_ccBagFloat", createHashMap];
};
if (_mode == "full") then {
{
    private _class = _x;
    private _released = (_float getOrDefault [_class, []]) select {(_now - (_x # 1)) < _ttl};
    private _ranked = _released apply {[(_x # 0) + ((_now - (_x # 1)) max 0), _x]};
    _ranked sort false;
    for "_i" from 1 to (_counts get _class) do {
        private _warm = 0;
        if !(_ranked isEqualTo []) then {_warm = (_ranked deleteAt 0) # 0;};
        _entries pushBack [_class, _warm];
    };
    _float set [_class, _ranked apply {_x # 1}];
} forEach keys _counts;
};
missionNamespace setVariable ["ACME_ccBagFloat", _float];
_advanced set [2, _entries];
if ((_box getVariable ["ACME_boxCoolerClass", ""]) != _base) then {
    _box setVariable ["ACME_boxCoolerClass", _base, true];
};
if ((_box getVariable ["ACME_boxCoolantStart", -1]) != (_advanced # 1)) then {
    _box setVariable ["ACME_boxCoolantStart", _advanced # 1, true];
};
// Warm exposure between unchanged contents is derivable from the last public
// sample. Keep the current server sample private instead of broadcasting an
// idle box every five seconds. Cargo changes and initialization publish a new baseline.
private _publish = count _previous != 4;
if (!_publish) then {
    _publish = (_previous # 0) != (_advanced # 0) || {(_previous # 1) != (_advanced # 1)}
        || {!(((_previous # 2) apply {_x # 0}) isEqualTo ((_advanced # 2) apply {_x # 0}))};
};
_box setVariable ["ACME_boxCoolerState", _advanced, _publish];
_advanced
