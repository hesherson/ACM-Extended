/* Retry one certified inventory request. Pending replication is never called depletion. */
params [["_patient",objNull,[objNull]],["_draw",false,[false]]];
if (isNull _patient || {!local _patient}) exitWith {};
private _session=_patient getVariable ["ACME_vent_o2Session",""];
if (_session=="") exitWith {};
private _source=_patient getVariable ["ACME_vent_o2Source",objNull];
if (isNull _source || {!alive _patient}
    || {(_patient getVariable ["ACME_vent_o2Epoch",-1])!=([_patient] call ACME_fnc_clinicalEpoch)}
    || {(_patient getVariable ["ACME_vent_o2Custody",""])!=(_patient getVariable ["ACME_vent_custodyId",""])}
    || {!(_patient getVariable ["ACME_vent_onPatient",false])}) exitWith {[_patient] call ACME_fnc_ventOxygenClear;};
private _pending=+(_patient getVariable ["ACME_vent_o2Pending",[]]);
if (count _pending==0) then {
    if (!_draw && {serverTime<(_patient getVariable ["ACME_vent_o2NextProbe",-1])}) exitWith {};
    private _sequence=(_patient getVariable ["ACME_vent_o2Sequence",0])+1;
    _patient setVariable ["ACME_vent_o2Sequence",_sequence,true];
    _pending=[_session,_sequence,if (_draw) then {"draw"} else {"probe"},serverTime];
    _patient setVariable ["ACME_vent_o2Pending",_pending,true];
    if (_draw) then {_patient setVariable ["ACME_vent_o2Status","DRAWING",true];};
};
if (count _pending!=4) exitWith {};
private _retry=_patient getVariable ["ACME_vent_o2Retry",[]];
if (count _retry==2 && {(_retry select 0)==(_pending select 1)} && {serverTime<(_retry select 1)}) exitWith {};
_patient setVariable ["ACME_vent_o2Retry",[_pending select 1,serverTime+1],false];
["ACME_ventOxygenDraw",[_patient,_source,_pending select 0,_pending select 1,_pending select 2,0],_source] call CBA_fnc_targetEvent;
