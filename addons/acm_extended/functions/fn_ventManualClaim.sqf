/* Owner high-water admission for an operator's monotonic manual breath command.
   One row per provider prevents an accepted command from becoming replayable after
   bounded UI receipt history ages out. Runtime state follows patient locality and
   is never recreated from an old medical snapshot. */
params [["_patient",objNull,[objNull]],["_medic",objNull,[objNull]],["_custody","",[""]],
    ["_epoch",-1,[0]],["_episodeId",-1,[0]],["_sequence",0,[0]],["_id","",[""]],["_simple",false,[false]]];
if (isNull _patient || {!local _patient} || {isNull _medic}
    || {!finite _sequence} || {_sequence<1} || {floor _sequence!=_sequence}
    || {_epoch!=([_patient] call ACME_fnc_clinicalEpoch)}
    || {_custody==""} || {_custody!=(_patient getVariable ["ACME_vent_custodyId",""])}
    || {!((missionNamespace getVariable ["ACME_vent_simpleMode",false]) isEqualTo _simple)}) exitWith {false};
private _episode=_patient getVariable ["ACME_vent_simpleEpisode",[false,0]];
if (_episodeId!=(_episode select 1) || {!((_episode select 0) isEqualTo _simple)}) exitWith {false};
private _provider=netId _medic;
private _canonical=format ["ventManual:%1:%2:%3:%4:%5",_provider,_epoch,_custody,_episodeId,_sequence];
if (_provider=="" || {_id!=_canonical}) exitWith {false};
private _commands=_patient getVariable ["ACME_vent_manualCommands",createHashMap];
private _last=_commands getOrDefault [_provider,[]];
if (count _last>0 && {_sequence<=(_last select 0)}) exitWith {false};
_commands set [_provider,[_sequence,_custody,_epoch,_episodeId]];
_patient setVariable ["ACME_vent_manualCommands",_commands,true];
true
