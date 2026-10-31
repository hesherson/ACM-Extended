/* One on-demand server registry operation and one self action. No world scan or idle cleanup worker. */
if (missionNamespace getVariable ["ACME_litterRegistered",false]) exitWith {};
missionNamespace setVariable ["ACME_litterRegistered",true];
["ACME_medicalLitter",{if (isServer) then {isNil {_this call ACME_fnc_medicalLitterServer;};};}] call CBA_fnc_addEventHandler;
["ACME_medicalLitterReply",{_this call ACME_fnc_medicalLitterReply;}] call CBA_fnc_addEventHandler;
if (!hasInterface) exitWith {};
private _action = ["ACME_CollectMedicalLitter","Collect medical litter","\a3\ui_f\data\IGUI\Cfg\Actions\take_ca.paa",
    {[_player] call ACME_fnc_medicalLitterRequest;},
    {[_player] call ACME_fnc_medicalLitterCanCollect;}
] call ace_interact_menu_fnc_createAction;
["CAManBase",1,["ACE_SelfActions","ACE_Equipment"],_action,true] call ace_interact_menu_fnc_addActionToClass;
