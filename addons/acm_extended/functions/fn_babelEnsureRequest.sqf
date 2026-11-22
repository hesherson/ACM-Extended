/* B391: ask every client to make sure ACRE2 Babel can carry garbled speech (fn_babelEnsure.sqf). Published once:
 * players joining later read the flag on start. Nothing happens to any mission until someone is impaired. */
if (isNil "acre_api_fnc_babelSetSpeakingLanguage") exitWith {};
if !(missionNamespace getVariable ["ACME_conscBabel", true]) exitWith {};
call ACME_fnc_babelEnsure;
if (missionNamespace getVariable ["ACME_babelActive", false]) exitWith {};
missionNamespace setVariable ["ACME_babelActive", true, true];
// one JIP event for the whole mission (the same id replaces itself): every client and every later joiner prepares
["ACME_babelEnsure", [], "ACME_babelEnsure"] call CBA_fnc_globalEventJIP;
