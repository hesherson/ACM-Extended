#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Adds an entry to the specified medical log of the unit.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: Log Type <STRING>
 * 2: Message <STRING>
 * 3: Formatting Arguments <ARRAY>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, "activity", "Message %1", ["Name"]] call ace_medical_treatment_fnc_addToLog
 *
 * Public: No
 */

params ["_unit", "_logType", "_message", "_arguments"];

private _me = missionNamespace getVariable ["ACE_player", player];
if (!isNull _me && {!isNull _unit}) then {[_me, _unit] call ACME_fnc_emmaMarkContact;};
private _out = [_unit, _logType, _message, _arguments] call ACME_fnc_ivLogRelabel;
if ((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true) then {
    _out params [["_lp", objNull], ["_lt", ""], ["_lf", ""], ["_la", []]];
    private _term = [_lf] call ACME_fnc_clinTerm;
    if (_term isNotEqualTo "") then {_lf = _term;};
    if (_la isEqualType []) then {
        private _copy = +_la;
        {
            if (_x isEqualType "") then {
                private _c = [_x] call ACME_fnc_clinTerm;
                if (_c isNotEqualTo "") then {_copy set [_forEachIndex, _c];};
            };
        } forEach _copy;
        _la = _copy;
    };
    _out = [_lp, _lt, _lf, _la];
};
_out params ["_unit", "_logType", "_message", "_arguments"];

if (!local _unit) exitWith {
    [QACEGVAR(medical_treatment,addToLog), _this, _unit] call CBA_fnc_targetEvent;
};

date params ["", "", "", "_hour", "_minute"];
private _timeStamp = format ["%1:%2", _hour, [_minute, 2] call CBA_fnc_formatNumber];

private _logVarName = format ["ace_medical_log_%1", _logType];
private _log = _unit getVariable [_logVarName, []];

if (_logType == "quick_view" && {_message == "Pulse oximeter (%1): %2"}) then {
    _log = _log select {(_x param [0, ""]) != _message
        || {((_x param [2, []]) param [0, ""]) != (_arguments param [0, ""])}};
};
private _limit = [8, 32] select (_logType == "quick_view");
while {count _log >= _limit} do {
    _log deleteAt 0;
};

_log pushBack [_message, _timeStamp, _arguments, _logType];
_unit setVariable [_logVarName, _log, true];

private _allLogs = _unit getVariable ["ace_medical_allLogs", []];

if !(_logVarName in _allLogs) then {
    _allLogs pushBack _logVarName;
    _unit setVariable ["ace_medical_allLogs", _allLogs, true];
};
