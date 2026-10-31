#include "..\script_component.hpp"
/* One authoritative UI request, never global-broadcast creation. Native direct
 * generatePatient/generatePatients remain available to existing mission scripts.
 */
params ["_object","_location","_initiator",["_count",1],["_severity",0],["_type",0],["_faction","BLUFOR"],["_presetID",""],["_requestID",[]]];
if (isNull _object || {isNull _location} || {isNull _initiator}) exitWith {false};
if (_requestID isEqualTo []) then {
    GVAR(SpawnRequestSerial) = (missionNamespace getVariable [QGVAR(SpawnRequestSerial),0]) + 1;
    _requestID = [clientOwner,GVAR(SpawnRequestSerial)];
};
if (!isServer) exitWith {
    [QGVAR(requestTrainingPatient),[_object,_location,_initiator,_count,_severity,_type,_faction,_presetID,_requestID]] call CBA_fnc_serverEvent;
    true
};
if !(_faction in ["Civilian","BLUFOR"]) exitWith {false};
if !(_count in [0,1,2,3,4,5,6,7,8] && {_severity in [0,1,2,3,4,5]} && {_type in [0,1,2,3,4,5,6]}) exitWith {false};
if (!alive _initiator || {_initiator distance _object > 8}) exitWith {false};
private _seen = _object getVariable [QGVAR(SpawnRequests),[]];
if (_requestID in _seen) exitWith {false};
if (_presetID == "cbrn_random") then {
    private _chemical = ([] call FUNC(patientPreset)) select {(_x select 10) isNotEqualTo []};
    _presetID = (selectRandom _chemical) select 0;
};
if (_presetID != "" && {([_presetID] call FUNC(patientPreset)) isEqualTo []}) exitWith {false};
_seen pushBack _requestID;
if (count _seen > 32) then {_seen deleteAt 0;};
_object setVariable [QGVAR(SpawnRequests),_seen,false];
if (_count == 1) then {
    [_object,_location,_initiator,_severity,_type,true,_faction,_presetID] call FUNC(generatePatient);
} else {
    [_object,_location,_initiator,_count,_severity,_faction,_presetID,_type] call FUNC(generatePatients);
};
true
