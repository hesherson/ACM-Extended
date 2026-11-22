/* B391: on the player's own client, twice a second: while the player is confused or obtunded (and awake) what
 * they say comes out garbled to everyone, by voice and by radio (ACRE2 Babel: they speak "acme_garbled", which no
 * one speaks). A lucid moment of obtundation speaks clearly. The language they spoke before comes back when they
 * recover. Without ACRE nothing happens here (TFAR: fn_obtundedVoice.sqf mutes the obtunded as before). */
if (isNil "acre_api_fnc_babelSetSpeakingLanguage") exitWith {};
private _p = if (!isNil "ACE_player" && {!isNull ACE_player}) then {ACE_player} else {player};
if (isNull _p) exitWith {};
private _obtunded = _p getVariable ["ACME_obtunded", false];
private _confused = _p getVariable ["ACME_confused", false];
private _enabled = missionNamespace getVariable ["ACME_conscBabel", true];
private _lucid = _obtunded && {uiNamespace getVariable ["ACME_obtunded_lucidActive", false]};
private _want = _enabled && {alive _p} && {!(_p getVariable ["ACE_isUnconscious", false])} && {_obtunded || _confused} && {!_lucid};
private _saved = uiNamespace getVariable ["ACME_babelSaved", ""];
private _languages = missionNamespace getVariable ["acre_sys_core_languages", []];
private _currentId = missionNamespace getVariable ["ACRE_CURRENT_LANGUAGE_ID", 0];
private _current = (_languages param [_currentId, [""]]) param [0, ""];
if (_want) then {
    if !(missionNamespace getVariable ["ACME_babelReady", false]) then {call ACME_fnc_babelEnsureRequest;};
    if (_current != "acme_garbled") then {
        // what they spoke before, kept for their recovery (a language the player picks meanwhile is overridden)
        if (_saved == "") then {uiNamespace setVariable ["ACME_babelSaved", [_current, "-"] select (_current == "")];};
        ["acme_garbled"] call acre_api_fnc_babelSetSpeakingLanguage;
    };
} else {
    if (_saved != "") then {
        uiNamespace setVariable ["ACME_babelSaved", ""];
        if (_current == "acme_garbled") then {
            private _back = if (_saved == "-") then {"acme_common"} else {_saved};
            if !([_back] call acre_api_fnc_babelSetSpeakingLanguage) then {
                // the language is gone: the first one the player speaks
                private _spoken = missionNamespace getVariable ["ACRE_SPOKEN_LANGUAGES", [0]];
                ACRE_CURRENT_LANGUAGE_ID = _spoken param [0, 0];
            };
        };
    };
};
