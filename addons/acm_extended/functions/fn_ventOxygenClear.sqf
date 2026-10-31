/* Detach a supply session. Cylinder stays in its real inventory; spent gas is never refunded. */
params [["_patient",objNull,[objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};
{_patient setVariable [_x,"",true];} forEach ["ACME_vent_o2Session","ACME_vent_o2Custody"];
{_patient setVariable [_x,objNull,true];} forEach ["ACME_vent_o2Source","ACME_vent_o2Medic"];
_patient setVariable ["ACME_vent_o2Pending",[],true];
_patient setVariable ["ACME_vent_o2Status","NONE",true];
_patient setVariable ["ACME_vent_o2Epoch",-1,true];
_patient setVariable ["ACME_vent_o2VerifiedUntil",-1,true];
_patient setVariable ["ACME_vent_o2ReserveUnits",0,true];
_patient setVariable ["ACME_vent_o2Credit",0,true];
[_patient,"ACME_vent_effectiveFiO2",21] call ACME_fnc_setVarNet;
