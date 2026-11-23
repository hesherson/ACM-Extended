/* B392: keep ACRE2 Babel's language list in the same order on every client.
 * ACRE identifies a language by its position in each client's own list (acre_sys_core_languages): a speaker sends
 * the position of the language they speak, a listener checks that position against the positions they speak. Two
 * clients whose lists are ordered differently hear each other as gibberish. A mission adds its languages whenever its
 * own setup runs (init, a module, a spawned babelSetupMission), which on a player joining late can come before or
 * after ACME's two; so on this client, ACME's languages are always moved behind the mission's ones, in a fixed order:
 *     [mission languages in the order the mission added them..., "acme_common", "acme_garbled"]
 * The spoken list and the language being spoken are carried over by name, so nothing the mission chose changes.
 * If the mission has languages and never gave this player any (their spoken list is only ACME's common language),
 * the player is put back to what ACRE alone does: no spoken languages, speaking the first one.
 * Unscheduled, cheap when nothing is out of order. Returns true when something was changed. */
if (!hasInterface) exitWith {false};
private _languages = missionNamespace getVariable ["acre_sys_core_languages", []];
if (_languages isEqualTo []) exitWith {false};
private _mine = ["acme_common", "acme_garbled"];
private _names = ["Common", "Garbled"];
private _keys = _languages apply {_x param [0, ""]};
if ((_keys findIf {_x in _mine}) < 0) exitWith {false}; // ACME's languages are not on this client (yet)
private _mission = _languages select {!((_x param [0, ""]) in _mine)};
private _want = _mission + (_mine apply {[_x, _names select (_mine find _x)]});
private _spokenIds = missionNamespace getVariable ["ACRE_SPOKEN_LANGUAGES", []];
if !(_spokenIds isEqualType []) then {_spokenIds = [];};
private _spokenKeys = (_spokenIds select {_x isEqualType 0}) apply {_keys param [_x, ""]};
private _changed = false;

private _inOrder = count _keys >= 2 && {(_keys select [count _keys - 2, 2]) isEqualTo _mine} && {count (_keys select {_x in _mine}) == 2};
if (!_inOrder) then {
    private _currentId = missionNamespace getVariable ["ACRE_CURRENT_LANGUAGE_ID", 0];
    private _currentKey = _keys param [_currentId, ""];
    private _newKeys = _want apply {_x select 0};
    missionNamespace setVariable ["acre_sys_core_languages", _want];
    private _newSpoken = [];
    {
        private _i = _newKeys find _x;
        if (_i >= 0) then {_newSpoken pushBackUnique _i;};
    } forEach _spokenKeys;
    ACRE_SPOKEN_LANGUAGES = _newSpoken;
    private _i = _newKeys find _currentKey;
    ACRE_CURRENT_LANGUAGE_ID = if (_i >= 0) then {_i} else {_newSpoken param [0, 0]};
    _keys = _newKeys;
    _changed = true;
};

// the mission has its own languages but never set this player's: ACRE's own default, as without ACME
if (_mission isNotEqualTo [] && {_spokenKeys isEqualTo ["acme_common"]}) then {
    ACRE_SPOKEN_LANGUAGES = [];
    if ((_keys param [missionNamespace getVariable ["ACRE_CURRENT_LANGUAGE_ID", 0], ""]) == "acme_common") then {
        ACRE_CURRENT_LANGUAGE_ID = 0;
    };
    _changed = true;
};
_changed
