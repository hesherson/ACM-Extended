/* B391: the confused state. Awake, up and moving, but disoriented: speech comes out garbled (fn_conscSpeech.sqf)
 * and vision swims a little (fn_confusedTick.sqf). Milder than obtundation, which it gives way to.
 * Single writer of ACME_confused / ACME_confused_manual (public: every machine shows the speech the same way).
 * _this is [_unit, _on, _manual, _reason]. Players only, as obtundation. */
params ["_unit", "_on", ["_manual", false], ["_reason", ""]];
if (isNull _unit) exitWith {};
if (_on && {!isPlayer _unit}) exitWith {};
if (_on && {!_manual} && {!(missionNamespace getVariable ["ACME_sys_obtunded", false])}) exitWith {};
if (_on && {_unit getVariable ["ACE_isUnconscious", false]}) exitWith {};
if ((_unit getVariable ["ACME_confused", false]) isEqualTo _on && {(_unit getVariable ["ACME_confused_manual", false]) isEqualTo (_on && _manual)}) exitWith {};
_unit setVariable ["ACME_confused", _on, true];
_unit setVariable ["ACME_confused_manual", _on && _manual, true];
_unit setVariable ["ACME_confused_dwellSince", -1];
if (!_on) then {_unit setVariable ["ACME_confused_refractoryUntil", CBA_missionTime + (missionNamespace getVariable ["ACME_confused_refractory", 30])];};
// the speakers' clients need the garble language before anyone speaks it (fn_babelEnsure.sqf)
if (_on) then {call ACME_fnc_babelEnsureRequest;};
