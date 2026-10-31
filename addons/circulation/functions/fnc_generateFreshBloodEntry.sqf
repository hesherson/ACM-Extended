#include "..\script_component.hpp"
/*
 * Author: Blue
 * Generates new fresh blood entry based on patient, and returns relevant ID.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 * 1: Volume <NUMBER>
 *
 * Return Value:
 * 0: Fresh Blood Entry ID <NUMBER>
 *
 * Example:
 * [player] call ACM_circulation_fnc_generateFreshBloodEntry;
 *
 * Public: No
 */

params ["_patient", "_volume", ["_facts", []]];

private _frozen=count _facts==4 && {(_facts select 0) isEqualTo "freshV1"}
    && {(_facts select 1) isEqualType true} && {(_facts select 2) isEqualType 0} && {finite (_facts select 2)}
    && {(_facts select 3) isEqualType 0} && {finite (_facts select 3)}
    && {(_facts select 3)>=0} && {(_facts select 3)<=7} && {(_facts select 3)==floor (_facts select 3)};
if (_facts isNotEqualTo [] && {!_frozen}) exitWith {-1};
private _collectionTime=if (_frozen) then {_facts select 2} else {CBA_missionTime};
private _bloodType=if (_frozen) then {_facts select 3} else {[_patient] call FUNC(generateBloodType)};
private _alive=if (_frozen) then {_facts select 1} else {alive _patient};

private _freshBloodlist = (missionNamespace getVariable [QGVAR(FreshBloodList), createHashMap]);

// Unique fresh-blood item classes exist for IDs 1..512. Allocation is server-authoritative in B96, so scan the
// actual registry for the first free configured ID rather than deriving an ID from HashMap count. This also keeps
// holes safe if an entry is ever retired later. ID 0 is reserved by the compatibility seed entry.
private _id = 1;
while {_id <= 512 && {!((_freshBloodlist getOrDefault [_id, []]) isEqualTo [])}} do { _id = _id + 1; };
if (_id > 512) exitWith {-1};

_freshBloodlist set [_id, [_patient,_volume,_bloodType,_alive,_collectionTime]];

missionNamespace setVariable [QGVAR(FreshBloodList), _freshBloodlist, true];

_id;
