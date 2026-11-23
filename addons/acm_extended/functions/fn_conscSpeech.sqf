/* B391/B392: on the player's own client, twice a second: while the player is confused or obtunded (and awake) what
 * they say comes out garbled to everyone, by voice and by radio (ACRE2 Babel: they speak "acme_garbled", which no
 * one speaks). A lucid moment of obtundation speaks clearly. The language they spoke before comes back when they
 * recover. Without ACRE nothing happens here (TFAR: fn_obtundedVoice.sqf mutes the obtunded as before).
 * B392: every tick also keeps the language list in the same order as on every other client (fn_babelOrder.sqf), and
 * a player who is not impaired is never left speaking "acme_garbled", whatever happened before (a missed recovery,
 * a setting switched off, a respawn). */
if (isNil "acre_api_fnc_babelSetSpeakingLanguage") exitWith {};
if (missionNamespace getVariable ["ACME_babelReady", false]) then {call ACME_fnc_babelOrder;};
private _p = if (!isNil "ACE_player" && {!isNull ACE_player}) then {ACE_player} else {player};
if (isNull _p) exitWith {};
private _obtunded = _p getVariable ["ACME_obtunded", false];
private _confused = _p getVariable ["ACME_confused", false];
private _enabled = missionNamespace getVariable ["ACME_conscBabel", true];
private _lucid = _obtunded && {uiNamespace getVariable ["ACME_obtunded_lucidActive", false]};
private _want = _enabled && {alive _p} && {!(_p getVariable ["ACE_isUnconscious", false])} && {_obtunded || _confused} && {!_lucid};
private _saved = missionNamespace getVariable ["ACME_babelSaved", ""];
private _languages = missionNamespace getVariable ["acre_sys_core_languages", []];
private _keys = _languages apply {_x param [0, ""]};
private _currentId = missionNamespace getVariable ["ACRE_CURRENT_LANGUAGE_ID", 0];
private _current = _keys param [_currentId, ""];
if (_want) then {
    if !(missionNamespace getVariable ["ACME_babelReady", false]) then {call ACME_fnc_babelEnsureRequest;};
    if (_current != "acme_garbled") then {
        // what they spoke before, kept for their recovery (a language the player picks meanwhile is overridden)
        if (_saved == "") then {missionNamespace setVariable ["ACME_babelSaved", [_current, "-"] select (_current == "")];};
        ["acme_garbled"] call acre_api_fnc_babelSetSpeakingLanguage;
    };
} else {
    if (_saved != "") then {missionNamespace setVariable ["ACME_babelSaved", ""];};
    if (_current == "acme_garbled") then {
        // back to what they spoke before; if that is gone, the first language they speak; else ACRE's default
        private _spoken = missionNamespace getVariable ["ACRE_SPOKEN_LANGUAGES", []];
        if !(_spoken isEqualType []) then {_spoken = [];};
        private _first = _spoken param [0, -1];
        private _firstKey = if (_first isEqualType 0 && {_first >= 0}) then {_keys param [_first, ""]} else {""};
        private _back = if (_saved in ["", "-"] || {!(_saved in _keys)}) then {_firstKey} else {_saved};
        if (_back == "acme_garbled" || {_back == ""} || {!([_back] call acre_api_fnc_babelSetSpeakingLanguage)}) then {
            ACRE_CURRENT_LANGUAGE_ID = 0;
        };
    };
};
