/* B391/B392: on this client, make ACRE2 Babel able to carry garbled speech, without changing what a mission does
 * with its own languages. ACRE garbles a speaker for a listener when the language the speaker uses is not one the
 * listener speaks; with no languages at all nobody is ever garbled. So every client adds the same two languages,
 * "acme_common" and "acme_garbled", and fn_babelOrder.sqf keeps them behind the mission's languages on every client
 * (ACRE compares languages by their position in each client's list, so the order must match everywhere):
 *  - a mission that uses Babel keeps its languages and each player's spoken list; no one speaks ACME's two;
 *  - a mission without Babel: everyone speaks "acme_common" (everyone understands everyone, as before).
 * A confused or obtunded player speaks "acme_garbled" while impaired (fn_conscSpeech.sqf). Runs once per client. */
if (!hasInterface || {isNil "acre_api_fnc_babelAddLanguageType"}) exitWith {};
if (missionNamespace getVariable ["ACME_babelReady", false]) exitWith {};
private _keys = (missionNamespace getVariable ["acre_sys_core_languages", []]) apply {_x param [0, ""]};
private _missionHasLanguages = (_keys findIf {!(_x in ["acme_common", "acme_garbled"])}) >= 0;
if !("acme_common" in _keys) then {["acme_common", "Common"] call acre_api_fnc_babelAddLanguageType;};
if !("acme_garbled" in _keys) then {["acme_garbled", "Garbled"] call acre_api_fnc_babelAddLanguageType;};
if (!_missionHasLanguages && {(missionNamespace getVariable ["ACRE_SPOKEN_LANGUAGES", []]) isEqualTo []}) then {
    ["acme_common"] call acre_api_fnc_babelSetSpokenLanguages;
};
call ACME_fnc_babelOrder;
ACME_babelReady = true;
