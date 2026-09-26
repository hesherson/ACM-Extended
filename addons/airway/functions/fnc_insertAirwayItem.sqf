#include "..\script_component.hpp"
/*
 * Author: Blue
 * Attempt to insert airway item
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Airway type <STRING>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget, "OPA"] call ACM_airway_fnc_insertAirwayItem;
 *
 * Public: No
 */

params ["_medic", "_patient", "_type"];

if ((_patient getVariable ["ACME_lido_seizureState", ""]) == "active") exitWith {
    if (_medic == ACE_player) then {
        ["Cannot place an airway adjunct: the patient is actively seizing. Control the seizure first.", 2, ACE_player, 13] call ACEFUNC(common,displayTextStructured);
    };
};

private _item = LLSTRING(OPA);
private _classname = "ACM_OPA";
private _airwayItem = _patient getVariable [QGVAR(AirwayItem_Oral), ""];

switch (_type) do {
    case "NPA": {
        _item = LLSTRING(NPA);
        _classname = "ACM_NPA";
        _airwayItem = _patient getVariable [QGVAR(AirwayItem_Nasal), ""];
    };
    case "SGA": {
        _item = LLSTRING(IGel);
        _classname = "ACM_IGel";
    };
    default {};
};

// NRB can coexist with OPA/NPA only. An i-gel needs a BVM or ventilator interface, so require the mask to be
// removed before the SGA is inserted. The treatment consumed the item before this callback, so return it here.
if (_type == "SGA" && {_patient getVariable ["ACME_nrb_on", false]}) exitWith {
    ["Remove the NRB before inserting an i-gel. Use BVM or ventilator support after placement.", 2.5, _medic] call ACEFUNC(common,displayTextStructured);
    [_medic, _classname] call ACEFUNC(common,addToInventory);
};

if (!(IS_UNCONSCIOUS(_patient)) && alive _patient) exitWith {
    private _hint = format [LLSTRING(Adjunct_Failed), _item];
    [format ["%1<br />%2", _hint, LLSTRING(Adjunct_Failed_Awake)], 2, _medic] call ACEFUNC(common,displayTextStructured);
    [_medic, _classname] call ACEFUNC(common,addToInventory);
};

if (_airwayItem != "") exitWith {
    [LSTRING(Adjunct_Already), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
    [_medic, _classname] call ACEFUNC(common,addToInventory);
};

if ((_patient getVariable [QGVAR(AirwayObstructionVomit_State), 0]) + (_patient getVariable [QGVAR(AirwayObstructionBlood_State), 0]) > 0) exitWith {
    private _hint = format [LLSTRING(Adjunct_Failed), _item];
    [format ["%1<br />%2", _hint, LLSTRING(CheckAirway_Obstruction)], 2, _medic] call ACEFUNC(common,displayTextStructured);
    [_medic, _classname] call ACEFUNC(common,addToInventory);
};

private _effectiveInflammation = (
    GET_AIRWAY_INFLAMMATION(_patient) +
    (_patient getVariable ["ACM_burns_AirwayInflammation",0])
) min 100;
if (_type == "SGA" && {_effectiveInflammation > AIRWAY_INFLAMMATION_THRESHOLD_SERIOUS}) exitWith {
    private _hint = format [LLSTRING(Adjunct_Failed), _item];
    [format ["%1<br />%2", _hint, LLSTRING(Adjunct_Failed_Inflammation)], 2, _medic] call ACEFUNC(common,displayTextStructured);
    [_medic, _classname] call ACEFUNC(common,addToInventory);
};

[format [LLSTRING(Adjunct_%1_Inserted), _item], 1.5, _medic] call ACEFUNC(common,displayTextStructured);
[_patient, _item] call ACEFUNC(medical_treatment,addToTriageCard);
[_patient, "activity", LSTRING(Adjunct_ActionLog), [[_medic, false, true] call ACEFUNC(common,getName), _item]] call ACEFUNC(medical_treatment,addToLog);

if (_type == "NPA") then {
    _patient setVariable [QGVAR(AirwayItem_Nasal), _type, true];
} else {
    _patient setVariable [QGVAR(AirwayItem_Oral), _type, true];
};
