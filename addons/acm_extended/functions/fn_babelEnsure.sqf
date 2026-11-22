/* B391: on this client, make ACRE2 Babel able to carry garbled speech, without changing a mission's own languages.
 * ACRE garbles a speaker for a listener when the language the speaker uses is not one the listener speaks; with
 * no languages at all nobody is ever garbled. So:
 *  - a mission that uses Babel keeps its languages and each player's spoken list; "acme_garbled" is added at the
 *    end, and no one speaks it;
 *  - a mission without Babel gets one common language that everyone speaks (as before: everyone understands
 *    everyone) and "acme_garbled".
 * A confused or obtunded player speaks "acme_garbled" while impaired (fn_conscSpeech.sqf). Runs once per client. */
if (!hasInterface || {isNil "acre_api_fnc_babelAddLanguageType"}) exitWith {};
if (missionNamespace getVariable ["ACME_babelReady", false]) exitWith {};
private _languages = missionNamespace getVariable ["acre_sys_core_languages", []];
private _keys = _languages apply {_x select 0};
if (_keys isEqualTo []) then {
    ["acme_common", "Common"] call acre_api_fnc_babelAddLanguageType;
    ["acme_garbled", "Garbled"] call acre_api_fnc_babelAddLanguageType;
    ["acme_common"] call acre_api_fnc_babelSetSpokenLanguages;
} else {
    if !("acme_garbled" in _keys) then {["acme_garbled", "Garbled"] call acre_api_fnc_babelAddLanguageType;};
};
ACME_babelReady = true;
