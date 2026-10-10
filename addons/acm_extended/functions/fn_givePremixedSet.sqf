/* Stage-to-clamp handoff. The set stays in the medic's custody until owner acceptance. */
params ["_set", "_patient", "_part", "_iv", "_site", "_action"];
if (isNull _patient || {_iv && {_site < 0}}) exitWith {};
private _blocked = [_patient, _part, _iv, _site] call ACME_fnc_preparedAttachBlockReason;
if (_blocked != "") exitWith {[ACE_player, [_blocked] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;};
_set params ["_uid", "_item", "", "", "", "", "_label"];
private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;
private _type = getText (_cfg >> "type");
private _content = (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap]) getOrDefault [toLowerANSI _type, []];
if (_content isEqualTo []) exitWith {
    ["This staged bag has no premixed medication definition.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _volume = getNumber (_cfg >> "volume");
if (_volume <= 0) exitWith {};
_content params ["_med", "_dose"];
private _remaining = _set param [9, 0];
if (_remaining > 0) then {_dose = _dose * ((_remaining / _volume) min 1);};
private _duration = (missionNamespace getVariable ["ACME_infusion_defaultDurationSeconds", createHashMap]) getOrDefault [_med, 600];
private _prepared = [_uid, _item, _action, _med, _dose, _duration, ACME_infusion_defaultDropSet, 0, 0, CBA_missionTime, _volume, 0, ACE_player, objNull];
private _args = [ACE_player, _patient, ACE_player, _item, _action, objNull, _part, _iv, _site, _volume, _prepared, -1, _label, _set];
private _pending = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
if (((values _pending) findIf {(!(_x select 2)) && {(((_x select 0) select 10) select 0) == _uid}}) >= 0) exitWith {};
if (((ACE_player getVariable ["ACME_preparedIVSets", []]) findIf {(_x select 0) == _uid}) < 0) exitWith {
    [ACE_player, ["prepared-set-missing"] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;
};
[_args] call ACME_fnc_preparedAttachRequest;
