params ["_patient","_kind",["_manual",false],["_spot",[]]];
private _actor=call ACME_fnc_controlledProvider;
if (isNull _actor || {!local _actor} || {!alive _actor}) exitWith {};
if (!_manual && {isNull _patient}) exitWith {};
[1.5,[_patient,_kind,_manual,_spot,_actor],{
    (_this select 0) params ["_patient","_kind","_manual","_spot","_actor"];
    [_actor,_patient,_kind,"setup",_manual,_spot] remoteExecCall ["ACME_fnc_equipmentRequest",2];
},{},"Setting up equipment",{
    (_this select 0) params ["_patient","","_manual","","_actor"];
    alive _actor && {isNull objectParent _actor} && {_manual || {!isNull _patient && {_actor distance _patient<=4}}}
}] call ace_common_fnc_progressBar;
