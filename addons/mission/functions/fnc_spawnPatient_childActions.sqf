#include "..\script_component.hpp"
/* B216: the existing training computer, shared by single and mass casualties.
 * Every parent remains executable: faction/triage/count parents spawn random
 * casualties; CBRN selects one of the absorbed-exposure training cases.
 */
params ["_object", "_spawnLocation", ["_count",1], ["_stage","faction"], ["_faction","BLUFOR"], ["_severity",0]];
private _rows = [];
switch (_stage) do {
    case "faction": {
        {
            _rows pushBack [_x,_x,"",0,0,"",if (_count == 0) then {"count"} else {"category"},_count,_x];
        } forEach ["Civilian","BLUFOR"];
    };
    case "count": {
        for "_n" from 2 to 8 do {
            _rows pushBack [str _n,str _n,"",0,0,"","category",_n,_faction];
        };
    };
    case "category": {
        {
            _x params ["_triage","_label","_color"];
            _rows pushBack [_label,_label,_color,_triage,0,"","case",_count,_faction];
        } forEach [[1,"Routine","#1be600"],[2,"Priority","#d19200"],[3,"Immediate","#d10000"],[4,"Expectant","#171717"]];
        _rows pushBack ["CBRN","CBRN","#a7d35b",5,0,"cbrn_random","case",_count,_faction];
    };
    case "case": {
        // Retain the original injury-mechanism choices alongside precise cases.
        private _mechanisms = switch (_severity) do {
            case 1: {[[1,"Gunshot"],[2,"Shrapnel"],[5,"Falling"],[6,"Backblast"]]};
            case 2: {[[1,"Gunshot"],[2,"Shrapnel"],[3,"Explosion"],[4,"Collision"]]};
            case 3: {[[1,"Gunshot"],[3,"Explosion"]]};
            default {[]};
        };
        {
            _x params ["_type","_label"];
            _rows pushBack [_label,_label,"",_severity,_type,"","",_count,_faction];
        } forEach _mechanisms;
        {
            _x params ["_id","_label","_triage"];
            private _chemical = (_x select 10) isNotEqualTo [];
            if ((_severity == 5 && {_chemical}) || {_severity == _triage && {!_chemical}}) then {
                _rows pushBack [_id,_label,"",_triage,0,_id,"",_count,_faction];
            };
        } forEach ([] call FUNC(patientPreset));
    };
};
private _actions = [];
{
    _x params ["_key","_label","_color","_triage","_type","_preset","_next","_number","_side"];
    private _args = [_object,_spawnLocation,_number,_triage,_type,_side,_preset,_next];
    _actions pushBack [[format ["ACM_Training_SpawnPatient_%1_%2_%3_%4",_side,_number,_stage,_key],
        _label, ["",_color], {
            params ["","_initiator","_args"];
            _args params ["_object","_location","_count","_severity","_type","_faction","_preset"];
            [_object,_location,_initiator,_count,_severity,_type,_faction,_preset] call FUNC(requestTrainingPatient);
        }, {true}, {
            params ["","","_args"];
            _args params ["_object","_location","_count","_severity","","_faction","","_next"];
            if (_next == "") exitWith {[]};
            [_object,_location,_count,_next,_faction,_severity] call FUNC(spawnPatient_childActions);
        }, _args] call ACEFUNC(interact_menu,createAction),[],_object];
} forEach _rows;
_actions
